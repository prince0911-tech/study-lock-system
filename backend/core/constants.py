from __future__ import annotations


APP_NAME = "StudyLockSystem"
API_HOST = "127.0.0.1"
API_PORT = 8765

ESSENTIAL_PROCESS_NAMES = {
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "explorer.exe",
    "dwm.exe",
    "fontdrvhost.exe",
    "startmenuexperiencehost.exe",
    "searchhost.exe",
    "runtimebroker.exe",
    "sihost.exe",
    "shellhost.exe",
    "textinputhost.exe",
    "securityhealthservice.exe",
    "securityhealthsystray.exe",
    "widgetservice.exe",
    "widgets.exe",
}

DEFAULT_ALLOWED_APPS = [
    "code.exe",
    "cursor.exe",
    "notion.exe",
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "opera_gx.exe",
    "vivaldi.exe",
    "jupyter-lab.exe",
    "jupyter-notebook.exe",
    "pycharm64.exe",
    "devenv.exe",
    "sublime_text.exe",
    "obsidian.exe",
    "acrord32.exe",
]

DEFAULT_BLOCKED_APPS = [
    "discord.exe",
    "steam.exe",
    "epicgameslauncher.exe",
    "telegram.exe",
    "whatsapp.exe",
    "taskmgr.exe",
    "vlc.exe",
    "spotify.exe",
]

BROWSER_PROCESS_NAMES = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "opera_gx.exe",
    "vivaldi.exe",
}

DEFAULT_ALLOWED_SITES = [
    "chatgpt.com",
    "openai.com",
    "youtube.com",
    "youtu.be",
    "github.com",
    "stackoverflow.com",
    "docs.python.org",
    "kaggle.com",
    "colab.research.google.com",
    "notion.so",
    "wikipedia.org",
    "coursera.org",
    "udemy.com",
]

DEFAULT_BLOCKED_SITES = [
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "reddit.com",
    "netflix.com",
    "primevideo.com",
    "hotstar.com",
    "twitch.tv",
    "discord.com",
]

STUDY_KEYWORDS = {
    "tutorial",
    "lecture",
    "course",
    "python",
    "java",
    "javascript",
    "sql",
    "assignment",
    "machine learning",
    "data science",
    "kaggle",
    "documentation",
    "reference",
    "notebook",
    "research",
    "exam",
    "study",
    "stack overflow",
    "github",
    "jupyter",
}

DISTRACTION_KEYWORDS = {
    "meme",
    "prank",
    "shorts",
    "reel",
    "mrbeast",
    "trailer",
    "music video",
    "highlights",
    "funny",
    "gaming",
    "stream",
    "match reaction",
    "compilation",
    "celebrity",
    "vlog",
    "entertainment",
    "discord",
    "reddit",
}
