"""
==============================================================================
BISspec.IQ - Supabase Database & Authentication Infrastructure
==============================================================================
Replaces SQLite / Flask-SQLAlchemy with Supabase PostgreSQL & Auth.
Supports both live Supabase cloud instances and graceful fallback mode.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

# pyrefly: ignore [missing-import]
from flask_login import UserMixin
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger("bisspec.supabase")

# ==============================================================================
# USER MODEL (Flask-Login UserMixin Adapter for Supabase)
# ==============================================================================
class SupabaseUser(UserMixin):
    """
    Session user model compatible with Flask-Login and Supabase Auth.
    """
    def __init__(self, user_id: str, email: str, username: str, access_token: Optional[str] = None, metadata: Optional[Dict] = None):
        self.id = str(user_id)
        self.email = str(email or "").strip().lower()
        self.username = str(username or (email.split('@')[0] if email else 'Officer')).strip()
        self.access_token = access_token
        self.metadata = metadata or {}
        self.is_authenticated_user = True

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "metadata": self.metadata
        }

    def __repr__(self):
        return f"<SupabaseUser {self.username} ({self.email})>"


def _auto_load_dotenv():
    """Lightweight loader for .env file if SUPABASE credentials are in .env."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "..", ".env"),
        os.path.join(current_dir, ".env"),
    ]
    for env_path in candidates:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception as e:
                logger.debug(f"Notice reading {env_path}: {e}")

_auto_load_dotenv()

# ==============================================================================
# PERSISTENT LOCAL FALLBACK STORE (Used when SUPABASE_URL / KEY are not set)
# ==============================================================================
class LocalSupabaseFallback:
    """
    Persistent local fallback store that ensures registered accounts stay intact
    across server reboots, file changes, and browser sessions.
    Saves user accounts to sih/data/local_users.json.
    """
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.storage_file = os.path.join(data_dir, "local_users.json")
        
        self.users_by_id: Dict[str, Dict[str, Any]] = {}
        self.users_by_email: Dict[str, Dict[str, Any]] = {}
        self.users_by_username: Dict[str, Dict[str, Any]] = {}
        
        self._load_users()

    def _seed_default_account(self):
        admin_id = "00000000-0000-0000-0000-000000000001"
        pw_hash = generate_password_hash("Admin@12345")
        officer = {
            "id": admin_id,
            "email": "officer@bis.gov.in",
            "username": "bis_officer",
            "password_hash": pw_hash,
            "created_at": "2024-01-01T00:00:00+00:00",
            "role": "officer"
        }
        self.users_by_id[admin_id] = officer
        self.users_by_email["officer@bis.gov.in"] = officer
        self.users_by_username["bis_officer".lower()] = officer

    def _load_users(self):
        """Loads users from local_users.json file, or seeds defaults if file is missing."""
        self._seed_default_account()
        
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for user_dict in data:
                            uid = str(user_dict.get("id", ""))
                            email = str(user_dict.get("email", "")).strip().lower()
                            uname = str(user_dict.get("username", "")).strip()
                            if uid:
                                self.users_by_id[uid] = user_dict
                            if email:
                                self.users_by_email[email] = user_dict
                            if uname:
                                self.users_by_username[uname.lower()] = user_dict
            except Exception as e:
                logger.warning(f"Notice reading local user database ({self.storage_file}): {e}")
        else:
            self._save()

    def _save(self):
        """Saves current registered users to sih/data/local_users.json."""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(list(self.users_by_id.values()), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist user database to {self.storage_file}: {e}")

    def sign_up(self, email: str, password: str, username: str) -> Tuple[Optional[SupabaseUser], Optional[str]]:
        email_clean = email.strip().lower()
        uname_clean = username.strip()

        # Reload in case another thread/process wrote to the file
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for user_dict in data:
                            uid = str(user_dict.get("id", ""))
                            em = str(user_dict.get("email", "")).strip().lower()
                            un = str(user_dict.get("username", "")).strip()
                            if uid: self.users_by_id[uid] = user_dict
                            if em: self.users_by_email[em] = user_dict
                            if un: self.users_by_username[un.lower()] = user_dict
            except Exception:
                pass

        if email_clean in self.users_by_email:
            return None, f"An account with email '{email_clean}' already exists."
        if uname_clean.lower() in self.users_by_username:
            return None, f"The username '{uname_clean}' is already taken."

        user_id = str(uuid.uuid4())
        record = {
            "id": user_id,
            "email": email_clean,
            "username": uname_clean,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "role": "officer"
        }
        self.users_by_id[user_id] = record
        self.users_by_email[email_clean] = record
        self.users_by_username[uname_clean.lower()] = record
        
        # Persist to disk immediately so it remains intact permanently
        self._save()

        user = SupabaseUser(user_id=user_id, email=email_clean, username=uname_clean, metadata={"role": "officer"})
        return user, None

    def sign_in(self, identifier: str, password: str) -> Tuple[Optional[SupabaseUser], Optional[str]]:
        ident = identifier.strip()
        ident_lower = ident.lower()
        record = None

        # Reload file to ensure newest registrations are present
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for user_dict in data:
                            uid = str(user_dict.get("id", ""))
                            em = str(user_dict.get("email", "")).strip().lower()
                            un = str(user_dict.get("username", "")).strip()
                            if uid: self.users_by_id[uid] = user_dict
                            if em: self.users_by_email[em] = user_dict
                            if un: self.users_by_username[un.lower()] = user_dict
            except Exception:
                pass

        if "@" in ident:
            record = self.users_by_email.get(ident_lower)
        else:
            record = self.users_by_username.get(ident_lower)

        if not record:
            return None, "Invalid username/email or password."

        if not check_password_hash(record["password_hash"], password):
            return None, "Invalid username/email or password."

        user = SupabaseUser(
            user_id=record["id"],
            email=record["email"],
            username=record["username"],
            metadata={"role": record.get("role", "officer")}
        )
        return user, None

    def get_user(self, user_id: str) -> Optional[SupabaseUser]:
        rec = self.users_by_id.get(str(user_id))
        if not rec and os.path.exists(self.storage_file):
            self._load_users()
            rec = self.users_by_id.get(str(user_id))

        if not rec:
            return None
        return SupabaseUser(
            user_id=rec["id"],
            email=rec["email"],
            username=rec["username"],
            metadata={"role": rec.get("role", "officer")}
        )


# ==============================================================================
# SUPABASE SERVICE CLIENT
# ==============================================================================
DEFAULT_SUPABASE_URL = "https://jxkxhynrefnzrvugaxfk.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_LgMJbULPy8cIu7lQ6fTMhQ_4jgn8yxQ"

class SupabaseService:
    def __init__(self):
        raw_url = os.environ.get("SUPABASE_URL") or DEFAULT_SUPABASE_URL
        # Sanitize URL: strip any trailing /rest/v1, /rest/v1/, or trailing slashes
        self.url = raw_url.split("/rest/v1")[0].rstrip("/")
        self.key = (os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or DEFAULT_SUPABASE_KEY).strip()
        self.is_connected = False
        self.client = None
        self.fallback = LocalSupabaseFallback()

        self._initialize_client()

    def _initialize_client(self):
        """Attempts to initialize the real Supabase client via Python SDK."""
        if not self.url or not self.key or "your-project" in self.url:
            logger.info("Supabase: SUPABASE_URL / SUPABASE_KEY not set. Operating in resilient local Supabase simulation.")
            self.is_connected = False
            return

        try:
            # pyrefly: ignore [missing-import]
            from supabase import create_client
            self.client = create_client(self.url, self.key)
            self.is_connected = True
            logger.info(f"Supabase: Connected successfully to {self.url}")
        except Exception as e:
            logger.warning(f"Supabase: Connection attempt failed ({str(e)}). Falling back to resilient mode.")
            self.is_connected = False
            self.client = None

    def sign_up(self, email: str, password: str, username: str) -> Tuple[Optional[SupabaseUser], Optional[str]]:
        """
        Signs up a new user using Supabase Auth.
        Stores username in user_metadata and attempts upsert into 'profiles' table.
        """
        email_clean = email.strip().lower()
        username_clean = username.strip()

        if self.is_connected and self.client:
            try:
                # 1. Sign up via Supabase Auth
                res = self.client.auth.sign_up({
                    "email": email_clean,
                    "password": password,
                    "options": {
                        "data": {
                            "username": username_clean,
                            "role": "officer"
                        }
                    }
                })

                if not res.user:
                    return None, "Failed to create Supabase account. Please verify input credentials."

                user_id = str(res.user.id)
                access_token = getattr(res.session, 'access_token', None) if res.session else None

                # 2. Upsert profile record in 'profiles' table
                try:
                    self.client.table("profiles").upsert({
                        "id": user_id,
                        "username": username_clean,
                        "email": email_clean,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                except Exception as table_err:
                    logger.warning(f"Supabase profiles table notice: {table_err}")

                user = SupabaseUser(
                    user_id=user_id,
                    email=email_clean,
                    username=username_clean,
                    access_token=access_token,
                    metadata={"role": "officer"}
                )
                return user, None

            except Exception as e:
                err_msg = str(e)
                logger.error(f"Supabase sign_up error: {err_msg}")
                # Parse common Supabase error messages
                if "User already registered" in err_msg or "already exists" in err_msg:
                    return None, f"An account with email '{email_clean}' already exists. Please log in instead."
                return None, f"Supabase Registration error: {err_msg}"

        # Local fallback execution
        return self.fallback.sign_up(email_clean, password, username_clean)

    def sign_in(self, identifier: str, password: str) -> Tuple[Optional[SupabaseUser], Optional[str]]:
        """
        Authenticates a user via Supabase Auth.
        Supports signing in with either email or username.
        """
        ident = identifier.strip()
        email_to_auth = ident.lower()

        # Always permit the default officer demo account out of the box
        if (ident.lower() in ("bis_officer", "officer@bis.gov.in")) and password == "Admin@12345":
            return self.fallback.sign_in("bis_officer", password)

        if self.is_connected and self.client:
            try:
                # If username provided instead of email, resolve email from 'profiles' table
                if "@" not in ident:
                    try:
                        query_res = self.client.table("profiles").select("email").eq("username", ident).limit(1).execute()
                        if query_res.data and len(query_res.data) > 0:
                            email_to_auth = query_res.data[0]["email"]
                    except Exception as q_err:
                        logger.warning(f"Could not resolve username '{ident}' via profiles table: {q_err}")

                # Sign in with password via Supabase Auth
                auth_res = self.client.auth.sign_in_with_password({
                    "email": email_to_auth,
                    "password": password
                })

                if not auth_res.user:
                    return None, "Invalid username/email or password."

                user_id = str(auth_res.user.id)
                meta = getattr(auth_res.user, 'user_metadata', {}) or {}
                resolved_username = meta.get("username", ident)
                access_token = getattr(auth_res.session, 'access_token', None) if auth_res.session else None

                user = SupabaseUser(
                    user_id=user_id,
                    email=auth_res.user.email or email_to_auth,
                    username=resolved_username,
                    access_token=access_token,
                    metadata=meta
                )
                return user, None

            except Exception as e:
                err_msg = str(e)
                logger.error(f"Supabase sign_in error: {err_msg}")
                if "Email not confirmed" in err_msg or "email_not_confirmed" in err_msg:
                    return None, "Email is not confirmed yet. Please verify your email or disable 'Confirm email' in Supabase Settings."
                if "Invalid login credentials" in err_msg:
                    return None, "Invalid username/email or password. Please try again."
                return None, f"Supabase Authentication error: {err_msg}"

        # Local fallback execution
        return self.fallback.sign_in(ident, password)

    def get_user_by_id(self, user_id: str) -> Optional[SupabaseUser]:
        """Loads user for Flask-Login session management."""
        if not user_id:
            return None

        if str(user_id) == "00000000-0000-0000-0000-000000000001":
            return self.fallback.get_user(user_id)

        if self.is_connected and self.client:
            try:
                # Try fetching from profiles table
                res = self.client.table("profiles").select("*").eq("id", user_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    return SupabaseUser(
                        user_id=row["id"],
                        email=row.get("email", ""),
                        username=row.get("username", "Officer"),
                        metadata=row
                    )
            except Exception as e:
                logger.warning(f"Supabase get_user_by_id query failed: {e}")

        return self.fallback.get_user(user_id)

    def sign_out(self):
        """Signs out of Supabase."""
        if self.is_connected and self.client:
            try:
                self.client.auth.sign_out()
            except Exception as e:
                logger.warning(f"Supabase sign_out notice: {e}")


# Singleton instance
supabase_service = SupabaseService()
