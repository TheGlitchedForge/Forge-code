import json
import streamlit as st
import google.generativeai as genai
from datetime import datetime
import uuid

# ------------------------
# Configure API
# ------------------------
import os
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# ------------------------
# File paths
# ------------------------
USERS_FILE = "users.json"
CHANNELS_FILE = "channels.json"
POSTS_FILE = "posts.json"
COMMENTS_FILE = "comments.json"

# ------------------------
# Helpers
# ------------------------
# ------------------------
# Helpers
# ------------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
        return default

    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                raise ValueError("Empty JSON file")
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        with open(path, "w") as f:
            json.dump(default, f)
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
    users[username] = password
    save_json(USERS_FILE, users)
    return True, "Account created!"


def login(username, password):
    users = load_json(USERS_FILE, {})
    if username in users and users[username] == password:
        return True
    return False

# ------------------------
# Reddit: Channels
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

# ------------------------
# Reddit: Posts
# ------------------------
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

# ------------------------
# Reddit: Comments
# ------------------------
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
# MAIN UI SETUP
# ------------------------
st.set_page_config(page_title="Mega App", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "login"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

# ------------------------
# LOGIN PAGE
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
            st.error("Invalid username or password")

    if st.button("Create Account"):
        st.session_state.page = "signup"
        st.rerun()

# ------------------------
# SIGNUP PAGE
# ------------------------
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

    c1, c2, c3 = st.columns(3)
    if c1.button("🔎 Custom Search", use_container_width=True):
        st.session_state.page = "search"
        st.rerun()
    if c2.button("📜 Reddit", use_container_width=True):
        st.session_state.page = "reddit_home"
        st.rerun()
    if c3.button("🔒 Logout", use_container_width=True):
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
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(query)
            st.write(response.text)
        except:
            st.error("AI Search not available.")

    if st.button("Back"):
        st.session_state.page = "menu"
        st.rerun()

# ------------------------
# REDDIT HOME
# ------------------------
def reddit_home():
    st.title("📜 Reddit Home")

    choice = st.sidebar.radio("Menu", ["🏠 Home", "📢 Channels", "➕ Make Post", "🔥 Trending", "⬅ Back"])

    if choice == "🏠 Home":
        reddit_feed()
    elif choice == "📢 Channels":
        reddit_channels()
    elif choice == "➕ Make Post":
        reddit_make_post()
    elif choice == "🔥 Trending":
        reddit_trending()
    else:
        st.session_state.page = "menu"
        st.rerun()

# ------------------------
# REDDIT: FEED
# ------------------------
def reddit_feed():
    st.header("Latest Posts")
    posts = load_json(POSTS_FILE, {})
    comments = load_json(COMMENTS_FILE, {})

    for pid, p in reversed(posts.items()):
        with st.container(border=True):
            st.subheader(p["title"])
            st.write("Posted in:", p["channel"])
            st.write(p["text"])
            if p["media"]:
                st.image(p["media"])
            st.caption(f"By: {p['author']} | Tags: {', '.join(p['tags'])}")

            st.write("### Comments")
            if pid in comments:
                for c in comments[pid]:
                    st.write(f"**{c['author']}:** {c['text']}")

            ctext = st.text_input(f"Comment on {pid}", key=f"c_{pid}")
            if st.button("Post Comment", key=f"btn_{pid}"):
                add_comment(pid, st.session_state.username, ctext)
                st.rerun()

# ------------------------
# REDDIT: CHANNELS
# ------------------------
def reddit_channels():
    st.header("Channels")
    channels = load_json(CHANNELS_FILE, {})

    for name, c in channels.items():
        with st.container(border=True):
            st.subheader(name)
            st.write(c["description"])
            st.caption(f"Created by {c['creator']}")

    st.divider()
    st.subheader("Create Channel")
    name = st.text_input("Channel name")
    desc = st.text_area("Description")

    if st.button("Create"):
        ok, msg = create_channel(name, desc, st.session_state.username)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

# ------------------------
# REDDIT: MAKE POST
# ------------------------
def reddit_make_post():
    st.header("Create Post")
    channels = list(load_json(CHANNELS_FILE, {}).keys())

    if len(channels) == 0:
        st.warning("No channels yet.")
        return

    ch = st.selectbox("Channel", channels)
    title = st.text_input("Title")
    body = st.text_area("Text")
    tags = st.text_input("Tags (comma)").split(",")
    media = st.text_input("Image URL")

    if st.button("Post"):
        create_post(ch, st.session_state.username, title, body, tags, media)
        st.success("Post Created!")
        st.rerun()

# ------------------------
# REDDIT: TRENDING
# ------------------------
def reddit_trending():
    st.header("Trending Posts")
    posts = load_json(POSTS_FILE, {})

    # Simple trending algorithm: sort by number of comments, then newest.
    comments = load_json(COMMENTS_FILE, {})
    def score(pid, post):
        num_comments = len(comments.get(pid, []))
        # secondary score: recency (newer posts get a small boost)
        return (num_comments, post.get("created", ""))

    sorted_posts = sorted(posts.items(), key=lambda x: score(x[0], x[1]), reverse=True)

    if not sorted_posts:
        st.info("No posts yet.")
        return

    for pid, p in sorted_posts:
        with st.container(border=True):
            st.subheader(p.get("title", "(no title)"))
            st.write(p.get("text", ""))
            if p.get("media"):
                try:
                    st.image(p.get("media"))
                except Exception:
                    st.write("[Media could not be loaded]")
            st.caption(f"By: {p.get('author')} | Channel: {p.get('channel')} | Tags: {', '.join(p.get('tags', []))}")

            # show number of comments
            num_c = len(comments.get(pid, []))
            st.write(f"Comments: {num_c}")

            # quick actions
            if st.button("View Post", key=f"trend_view_{pid}"):
                st.session_state.page = "view_post"
                st.session_state.view_post_id = pid
                st.rerun()


# ------------------------
# View single post handler (used by Trending/Search/Feed)
# ------------------------
def view_post_page():
    pid = st.session_state.get("view_post_id")
    posts = load_json(POSTS_FILE, {})
    comments = load_json(COMMENTS_FILE, {})

    if not pid or pid not in posts:
        st.error("Post not found.")
        if st.button("Back"):
            st.session_state.page = "reddit_home"
            st.rerun()
        return

    p = posts[pid]
    st.header(p.get("title", "(no title)"))
    st.write("Channel:", p.get("channel"))
    st.write(p.get("text"))
    if p.get("media"):
        try:
            st.image(p.get("media"))
        except Exception:
            st.write("[Media could not be loaded]")
    st.caption(f"By: {p.get('author')} | Tags: {', '.join(p.get('tags', []))}")

    st.write("---")
    st.subheader("Comments")
    for c in comments.get(pid, []):
        st.write(f"**{c['author']}**: {c['text']}")

    new_c = st.text_input("Your comment", key=f"view_c_{pid}")
    if st.button("Post Comment", key=f"view_btn_{pid}"):
        if new_c.strip():
            add_comment(pid, st.session_state.username, new_c)
            st.success("Comment added")
            st.rerun()
        else:
            st.warning("Comment cannot be empty.")

    if st.button("Back"):
        st.session_state.page = "reddit_home"
        st.rerun()


# ------------------------
# APP ROUTER / MAIN
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
        elif st.session_state.page == "reddit_home":
            reddit_home()
        elif st.session_state.page == "reddit":
            reddit_home()
        elif st.session_state.page == "view_post":
            view_post_page()
        elif st.session_state.page == "reddit":
            reddit_home()
        else:
            # fallback to menu
            menu_page()

if __name__ == "__main__":
    main()
