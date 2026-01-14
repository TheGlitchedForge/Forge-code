import json
import streamlit as st
import google.generativeai as genai
from datetime import datetime
import uuid
import os
from streamlit_autorefresh import st_autorefresh

# ------------------------
# Configure API
# ------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ------------------------
# File paths
# ------------------------
USERS_FILE = "users.json"
CHANNELS_FILE = "channels.json"
POSTS_FILE = "posts.json"
COMMENTS_FILE = "comments.json"
CHAT_FILE = "chats.json"

# ------------------------
# JSON helpers
# ------------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f, indent=4)
        return default
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                raise ValueError("Empty JSON file")
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        with open(path, "w") as f:
            json.dump(default, f, indent=4)
        return default

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, path)

# ------------------------
# USER AUTH
# ------------------------
def signup(username, password):
    users = load_json(USERS_FILE, {})
    if username in users:
        return False, "Username already exists!"
    users[username] = {"password": password, "banned": False}  # support ban/kick
    save_json(USERS_FILE, users)
    return True, "Account created!"

def login(username, password):
    users = load_json(USERS_FILE, {})
    if username in users and users[username]["password"] == password:
        if users[username].get("banned"):
            return False
        return True
    return False

# ------------------------
# REDDIT HELPERS
# ------------------------
def create_channel(name, description, creator):
    channels = load_json(CHANNELS_FILE, {})
    if name in channels:
        return False, "Channel already exists!"
    channels[name] = {
        "description": description,
        "creator": creator,
        "created": str(datetime.now())
    }
    save_json(CHANNELS_FILE, channels)
    return True, "Channel created!"

def create_post(channel, author, title, text, tags, media_url=None):
    posts = load_json(POSTS_FILE, {})
    post_id = str(uuid.uuid4())
    posts[post_id] = {
        "channel": channel,
        "author": author,
        "title": title,
        "text": text,
        "tags": tags,
        "media": media_url,
        "created": str(datetime.now())
    }
    save_json(POSTS_FILE, posts)
    return True, post_id

def add_comment(post_id, author, text):
    comments = load_json(COMMENTS_FILE, {})
    if post_id not in comments:
        comments[post_id] = []
    comments[post_id].append({
        "id": str(uuid.uuid4()),
        "author": author,
        "text": text,
        "created": str(datetime.now())
    })
    save_json(COMMENTS_FILE, comments)
    return True

# ------------------------
# CHAT HELPERS
# ------------------------
def send_group_message(sender, message):
    chats = load_json(CHAT_FILE, {"group": {"messages": [], "members": []}, "dm": []})
    # ensure sender is in group
    if sender not in chats["group"]["members"]:
        chats["group"]["members"].append(sender)
    chats["group"]["messages"].append({
        "sender": sender,
        "message": message,
        "timestamp": str(datetime.now())
    })
    save_json(CHAT_FILE, chats)

def add_group_member(admin, user):
    chats = load_json(CHAT_FILE, {"group": {"messages": [], "members": []}, "dm": []})
    if user not in chats["group"]["members"]:
        chats["group"]["members"].append(user)
        save_json(CHAT_FILE, chats)
        return True
    return False

def remove_group_member(admin, user):
    chats = load_json(CHAT_FILE, {"group": {"messages": [], "members": []}, "dm": []})
    if user in chats["group"]["members"]:
        chats["group"]["members"].remove(user)
        save_json(CHAT_FILE, chats)
        return True
    return False

def send_dm(sender, receiver, message):
    chats = load_json(CHAT_FILE, {"group": {"messages": [], "members": []}, "dm": []})
    chats["dm"].append({
        "from": sender,
        "to": receiver,
        "message": message,
        "timestamp": str(datetime.now())
    })
    save_json(CHAT_FILE, chats)

def get_group_messages():
    chats = load_json(CHAT_FILE, {"group": {"messages": [], "members": []}, "dm": []})
    return chats["group"]["messages"], chats["group"]["members"]

def get_dm_messages(user1, user2):
    chats = load_json(CHAT_FILE, {"group": {"messages": [], "members": []}, "dm": []})
    return [m for m in chats["dm"] if (m["from"]==user1 and m["to"]==user2) or (m["from"]==user2 and m["to"]==user1)]

# ------------------------
# STREAMLIT SETUP
# ------------------------
st.set_page_config(page_title="Mega App", layout="wide")

if "page" not in st.session_state: st.session_state.page = "login"
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = None

# ------------------------
# LOGIN / SIGNUP
# ------------------------
def login_page():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "menu"
            st.rerun()
        else:
            st.error("Invalid username or banned")
    if st.button("Create Account"):
        st.session_state.page = "signup"
        st.rerun()

def signup_page():
    st.title("Create Account")
    new_user = st.text_input("Choose a username")
    new_pass = st.text_input("Choose a password", type="password")
    if st.button("Create Account"):
        ok, msg = signup(new_user, new_pass)
        if ok:
            st.success(msg)
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error(msg)
    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ------------------------
# MENU PAGE
# ------------------------
def menu_page():
    st.markdown("<h1 style='text-align:center; color:#4A90E2;'>Main Menu</h1>", unsafe_allow_html=True)
    st.write(f"Logged in as **{st.session_state.username}**")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🔎 Custom Search", use_container_width=True):
        st.session_state.page = "search"
        st.rerun()
    if c2.button("📜 Reddit", use_container_width=True):
        st.session_state.page = "reddit_home"
        st.rerun()
    if c3.button("💬 Chat", use_container_width=True):
        st.session_state.page = "chat"
        st.rerun()
    if c4.button("🔒 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.page = "login"
        st.rerun()

# ------------------------
# SEARCH PAGE
# ------------------------
def search_page():
    st.title("Custom Search")
    query = st.text_input("Ask something...")
    if st.button("Search"):
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(query)
            st.write(response.text)
        except:
            st.error("AI Search not available.")
    if st.button("Back"):
        st.session_state.page = "menu"
        st.rerun()

# ------------------------
# CHAT PAGE (GROUP + DM with GUI)
# ------------------------
def chat_page():
    st.title("💬 Chat")
    st.write(f"Logged in as **{st.session_state.username}**")

    # Back button
    if st.button("⬅ Back to Menu"):
        st.session_state.page = "menu"
        st.rerun()

    st_autorefresh(interval=2000, key="refresh")  # auto-refresh every 2 seconds

    tab = st.radio("Choose chat type:", ["Group Chat", "Direct Message"])

    if tab == "Group Chat":
        st.subheader("🌐 Group Chat")
        messages, members = get_group_messages()
        st.write(f"**Members:** {', '.join(members) if members else 'No members yet'}")
        
        # Admin controls: only first user is admin
        admin = members[0] if members else st.session_state.username
        if st.session_state.username == admin:
            st.markdown("**Admin Controls:**")
            add_user = st.text_input("Add member by username", key="add_member")
            if st.button("Add Member"):
                if add_group_member(admin, add_user):
                    st.success(f"{add_user} added to group")
                    st.experimental_rerun()
                else:
                    st.warning(f"{add_user} is already in group")
            kick_user = st.text_input("Kick member by username", key="kick_member")
            if st.button("Kick Member"):
                if kick_user != admin:
                    if remove_group_member(admin, kick_user):
                        st.success(f"{kick_user} removed from group")
                        st.experimental_rerun()
                    else:
                        st.warning(f"{kick_user} not in group")
                else:
                    st.error("Admin cannot be kicked!")

        for m in messages[-50:]:
            ts = m.get("timestamp", "")
            try:
                ts = ts.split("T")[1][:8]
            except:
                ts = ts[-8:]
            st.write(f"**{m['sender']}**: {m['message']} _(at {ts})_")

        msg = st.text_input("Enter message", key="group_msg_input")
        if st.button("Send Message"):
            if msg.strip():
                send_group_message(st.session_state.username, msg)
                st.experimental_rerun()

    else:
        st.subheader("✉️ Direct Messages")
        users = load_json(USERS_FILE, {})
        user_list = [u for u in users if u != st.session_state.username]
        if user_list:
            receiver = st.selectbox("Select user", user_list)
            if receiver:
                messages = get_dm_messages(st.session_state.username, receiver)
                for m in messages[-50:]:
                    ts = m.get("timestamp", "")
                    try:
                        ts = ts.split("T")[1][:8]
                    except:
                        ts = ts[-8:]
                    st.write(f"**{m['from']} → {m['to']}**: {m['message']} _(at {ts})_")

                dm_key = f"dm_msg_{receiver}"
                dm_msg = st.text_input("Enter message", key=dm_key)
                if st.button("Send DM", key=f"send_dm_{receiver}"):
                    if dm_msg.strip():
                        send_dm(st.session_state.username, receiver, dm_msg)
                        st.experimental_rerun()
        else:
            st.info("No other users to DM yet.")


# ------------------------
# MAIN APP ROUTER
# ------------------------
def main():
    if not st.session_state.logged_in:
        if st.session_state.page == "signup":
            signup_page()
        else:
            login_page()
    else:
        if st.session_state.page == "menu":
            menu_page()
        elif st.session_state.page == "search":
            search_page()
        elif st.session_state.page in ["reddit_home", "reddit"]:
            reddit_home()  # your existing reddit_home function
        elif st.session_state.page == "view_post":
            view_post_page()  # your existing view_post_page function
        elif st.session_state.page == "chat":
            chat_page()
        else:
            menu_page()

if __name__ == "__main__":
    main()
