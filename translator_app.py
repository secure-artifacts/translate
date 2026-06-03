import ctypes
import base64
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from ctypes import wintypes
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from tkinter import messagebox, ttk
from urllib import parse, request
from urllib.error import HTTPError, URLError


APP_TITLE = "AI 翻译助手"
APP_ICON = "app_icon.ico"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    bundled = Path(getattr(sys, "_MEIPASS", app_base_dir()))
    candidate = bundled / name
    if candidate.exists():
        return candidate
    return app_base_dir() / name


CONFIG_PATH = app_base_dir() / "translator_config.json"
FLOAT_TRANSPARENT_COLOR = "#ff00ff"
FLOAT_ACTIVE_COLOR = "#cfefff"
FLOAT_BORDER_COLOR = "#6aaed6"
FLOAT_INACTIVE_BORDER = "#8a96a6"
FLOAT_COLOR_PRESETS = {
    "blue": ("#cfefff", "color_preset_blue"),
    "green": ("#c8f7d4", "color_preset_green"),
    "purple": ("#e8ddff", "color_preset_purple"),
    "yellow": ("#fff2a8", "color_preset_yellow"),
    "pink": ("#ffd6ea", "color_preset_pink"),
    "white": ("#ffffff", "color_preset_white"),
    "custom": ("", "color_preset_custom"),
}

SPEECH_CULTURES = {
    "zh-CN": "zh-CN",
    "zh-TW": "zh-TW",
    "en": "en-US",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
    "it": "it-IT",
    "pt": "pt-BR",
    "ru": "ru-RU",
    "ar": "ar-SA",
    "hi": "hi-IN",
    "ne": "ne-NP",
    "my": "my-MM",
    "th": "th-TH",
    "vi": "vi-VN",
    "id": "id-ID",
    "nl": "nl-NL",
    "pl": "pl-PL",
    "tr": "tr-TR",
    "sv": "sv-SE",
    "uk": "uk-UA",
    "el": "el-GR",
    "he": "he-IL",
    "tl": "fil-PH",
}

BLUE = "#1a73e8"
TEXT = "#1f3552"
MUTED = "#7a8799"
BORDER = "#d7dee8"
BG = "#f5f8fc"
PANEL = "#ffffff"


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


PTR_BITS = ctypes.sizeof(ctypes.c_void_p) * 8
ULONG_PTR = ctypes.c_uint64 if PTR_BITS == 64 else ctypes.c_ulong
LONG_PTR = ctypes.c_int64 if PTR_BITS == 64 else ctypes.c_long
UINT_PTR = ctypes.c_uint64 if PTR_BITS == 64 else ctypes.c_uint


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


IS_WINDOWS = sys.platform.startswith("win")
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0
if IS_WINDOWS:
    USER32 = ctypes.WinDLL("user32", use_last_error=True)
    KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    SW_RESTORE = 9
    GA_ROOT = 2
    GW_HWNDNEXT = 2
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_RETURN = 0x0D
    VK_MENU = 0x12
    VK_A = 0x41
    VK_C = 0x43
    VK_D = 0x44
    VK_V = 0x56
    WH_KEYBOARD_LL = 13
    HC_ACTION = 0
    WM_KEYDOWN = 0x0100
    WM_SYSKEYDOWN = 0x0104
    LLKHF_INJECTED = 0x00000010
    KEYEVENTF_KEYUP = 0x0002
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    LRESULT = ctypes.c_ssize_t
    LOW_LEVEL_KEYBOARD_PROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, UINT_PTR, LONG_PTR)
    USER32.SetWindowsHookExW.argtypes = [ctypes.c_int, LOW_LEVEL_KEYBOARD_PROC, wintypes.HINSTANCE, wintypes.DWORD]
    USER32.SetWindowsHookExW.restype = wintypes.HHOOK
    USER32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, UINT_PTR, LONG_PTR]
    USER32.CallNextHookEx.restype = LRESULT
    USER32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    USER32.UnhookWindowsHookEx.restype = wintypes.BOOL
    USER32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    USER32.GetAsyncKeyState.restype = ctypes.c_short
    KERNEL32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    KERNEL32.GetModuleHandleW.restype = wintypes.HMODULE
else:
    USER32 = None
    KERNEL32 = None
    SW_RESTORE = 9
    GA_ROOT = 2
    GW_HWNDNEXT = 2
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_RETURN = 0x0D
    VK_MENU = 0x12
    VK_A = 0x41
    VK_C = 0x43
    VK_D = 0x44
    VK_V = 0x56
    WH_KEYBOARD_LL = 13
    HC_ACTION = 0
    WM_KEYDOWN = 0x0100
    WM_SYSKEYDOWN = 0x0104
    LLKHF_INJECTED = 0x00000010
    KEYEVENTF_KEYUP = 0x0002
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    LOW_LEVEL_KEYBOARD_PROC = None


HOTKEY_KEY_TO_VK = {chr(code): code for code in range(ord("A"), ord("Z") + 1)}
HOTKEY_KEY_TO_VK.update({str(number): ord(str(number)) for number in range(10)})
HOTKEY_KEY_TO_VK.update({f"F{number}": 0x6F + number for number in range(1, 13)})
HOTKEY_MODIFIER_VKS = {"Ctrl": VK_CONTROL, "Alt": VK_MENU, "Shift": VK_SHIFT}
HOTKEY_MODIFIER_ALIASES = {
    "CTRL": "Ctrl",
    "CONTROL": "Ctrl",
    "ALT": "Alt",
    "SHIFT": "Shift",
}
HOTKEY_MODIFIER_ORDER = ("Ctrl", "Alt", "Shift")


LANGUAGES = [
    ("zh-CN", "简体中文"),
    ("zh-TW", "繁体中文"),
    ("en", "英语"),
    ("hi", "印地语"),
    ("id", "印度尼西亚语"),
    ("ms", "马来语"),
    ("it", "意大利语"),
    ("tl", "菲律宾语"),
    ("ceb", "宿务语"),
    ("my", "缅甸语"),
    ("pt-BR", "葡萄牙语（巴西）"),
    ("pt-PT", "葡萄牙语（葡萄牙）"),
    ("pt", "葡萄牙语"),
    ("es", "西班牙语"),
    ("vi", "越南语"),
    ("lo", "老挝语"),
    ("th", "泰语"),
    ("hmn", "苗语"),
    ("ja", "日语"),
    ("zu", "祖鲁语"),
    ("hu", "匈牙利语"),
    ("hr", "克罗地亚语"),
    ("eo", "世界语"),
    ("ckb", "中库尔德语"),
    ("uz", "乌兹别克语"),
    ("hy", "亚美尼亚语"),
    ("sd", "信德语"),
    ("is", "冰岛语"),
    ("chr", "切罗基语"),
    ("gl", "加利西亚语"),
    ("ca", "加泰罗尼亚语"),
    ("kn", "卡纳达语"),
    ("lb", "卢森堡语"),
    ("rom", "吉普赛语"),
    ("kk", "哈萨克语"),
    ("iu", "因纽特语"),
    ("tr", "土耳其语"),
    ("tg", "塔吉克语"),
    ("see", "塞内卡语"),
    ("oj", "奥吉布瓦语"),
    ("osa", "奥塞治语"),
    ("cy", "威尔士语"),
    ("dz", "宗卡语"),
    ("km", "高棉语"),
    ("ko", "韩语"),
    ("ru", "俄语"),
    ("fr", "法语"),
    ("de", "德语"),
    ("mn", "蒙古语"),
    ("ne", "尼泊尔语"),
    ("af", "南非荷兰语"),
    ("ar", "阿拉伯语"),
    ("ta", "泰米尔语"),
    ("as", "阿萨姆语"),
    ("bn", "孟加拉语"),
    ("eu", "巴斯克语"),
    ("be", "白俄罗斯语"),
    ("bg", "保加利亚语"),
    ("cs", "捷克语"),
    ("da", "丹麦语"),
    ("nl", "荷兰语"),
    ("fi", "芬兰语"),
    ("ff", "富拉语"),
    ("su", "巽他语"),
    ("ku", "库尔德语"),
    ("yi", "意第绪语"),
    ("lv", "拉脱维亚语"),
    ("nn", "挪威尼诺斯克语"),
    ("ti", "提格利尼亚语"),
    ("sl", "斯洛文尼亚语"),
    ("ps", "普什图语"),
    ("ky", "柯尔克孜语"),
    ("ka", "格鲁吉亚语"),
    ("mi", "毛利语"),
    ("bs", "波斯尼亚语"),
    ("ht", "海地克里奥尔语"),
    ("ga", "爱尔兰语"),
    ("et", "爱沙尼亚语"),
    ("xh", "科萨语"),
    ("co", "科西嘉语"),
    ("lt", "立陶宛语"),
    ("so", "索马里语"),
    ("yo", "约鲁巴语"),
    ("nv", "纳瓦霍语"),
    ("sn", "绍纳语"),
    ("ug", "维吾尔语"),
    ("gd", "苏格兰盖尔语"),
    ("el", "希腊语"),
    ("gu", "古吉拉特语"),
    ("he", "希伯来语"),
    ("la", "拉丁语"),
    ("ml", "马拉雅拉姆语"),
    ("mni-Mtei", "曼尼普尔语"),
    ("mr", "马拉地语"),
    ("no", "挪威语"),
    ("or", "奥里亚语"),
    ("fa", "波斯语"),
    ("pl", "波兰语"),
    ("pa", "旁遮普语"),
    ("ro", "罗马尼亚语"),
    ("sa", "梵语"),
    ("sw", "斯瓦希里语"),
    ("sv", "瑞典语"),
    ("te", "泰卢固语"),
    ("uk", "乌克兰语"),
    ("ur", "乌尔都语"),
    ("si", "僧伽罗语"),
    ("sr", "塞尔维亚语"),
    ("sk", "斯洛伐克语"),
    ("bo", "藏语"),
    ("fy", "西弗里西亚语"),
    ("az", "阿塞拜疆语"),
    ("am", "阿姆哈拉语"),
    ("sq", "阿尔巴尼亚语"),
    ("tt", "鞑靼语"),
    ("mk", "马其顿语"),
    ("mg", "马拉加斯语"),
    ("mt", "马耳他语"),
    ("ny", "齐切瓦语"),
    ("ccp", "Chakma"),
    ("lis", "Lisu"),
    ("myh", "Makah"),
    ("mez", "Menominee"),
    ("one", "Oneida"),
    ("crk", "Plains Cree"),
    ("rhg", "Rohingya"),
    ("uzs", "Southern Uzbek"),
]

LANGUAGE_NAMES = dict(LANGUAGES)
LANGUAGE_CODES = {name: code for code, name in LANGUAGES}
LANGUAGE_LABELS = [name for _, name in LANGUAGES]

UI_LANGUAGES = [
    ("zh-CN", "中文（简体）"),
    ("zh-TW", "中文（繁體）"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("it", "Italiano"),
    ("pt", "Português"),
    ("ru", "Русский"),
    ("ar", "العربية"),
    ("hi", "हिन्दी"),
    ("ne", "नेपाली"),
    ("my", "မြန်မာ"),
    ("th", "ไทย"),
    ("vi", "Tiếng Việt"),
    ("id", "Bahasa Indonesia"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("tr", "Türkçe"),
    ("sv", "Svenska"),
    ("uk", "Українська"),
    ("el", "Ελληνικά"),
    ("he", "עברית"),
]
UI_LANGUAGE_NAMES = dict(UI_LANGUAGES)
UI_LANGUAGE_CODES = {name: code for code, name in UI_LANGUAGES}
UI_LANGUAGE_LABELS = [name for _, name in UI_LANGUAGES]

UI_TEXT = {
    "zh-CN": {
        "app_title": "AI 翻译助手",
        "ready": "准备就绪",
        "translate_tab": "翻译",
        "settings_tab": "设置",
        "font_tab": "文字大小",
        "display_tab": "界面语言",
        "text_tab": "文字",
        "direct_tab": "直译",
        "swap_languages": "⇅ 交换语言",
        "translate": "翻译",
        "copy_output": "复制译文",
        "clear": "清空",
        "listen_input": "麦克风",
        "speak_input": "朗读输入",
        "speak_output": "朗读译文",
        "back_translation": "回翻译",
        "back_to": "回翻译为：{source}",
        "always_on_top": "软件界面永远置顶",
        "ui_language": "软件界面显示语言",
        "translation_method": "翻译方式",
        "ai_translate": "AI 翻译",
        "google_translate": "Google 翻译",
        "microsoft_translate": "Microsoft 翻译",
        "microsoft_key": "Microsoft API KEY",
        "microsoft_region": "Microsoft 区域",
        "microsoft_key_help": "选择 Microsoft 回翻译时使用；也可以设置环境变量 MICROSOFT_TRANSLATOR_KEY / MICROSOFT_TRANSLATOR_REGION。",
        "ai_platform": "AI 平台",
        "country": "国家特色",
        "gender": "我的性别",
        "gemini_key": "Gemini API KEY",
        "gemini_key_help": "一行输入一个密钥；当前一个失败时会自动尝试下一行。",
        "gemini_model": "Gemini 模型",
        "groq_key": "Groq API KEY",
        "groq_key_help": "Groq 同样支持多行密钥轮换。",
        "groq_model": "Groq 模型",
        "my_languages": "我的语言（最多三种）",
        "their_languages": "对方语言（最多三种）",
        "back_setting": "回翻译",
        "back_platform_setting": "回翻译平台",
        "back_yes": "是，显示回翻译小界面",
        "back_no": "否，不进行回翻译",
        "direct_settings": "直译设置",
        "direct_hotkey_setting": "启动直译快捷键",
        "direct_hotkey_help": "同一个快捷键可来回开启/关闭直译。格式示例：Alt+Q、Ctrl+Shift+T、Ctrl+Alt+D。支持 Ctrl / Alt / Shift 加字母、数字或 F1-F12。",
        "direct_hotkey_invalid": "直译快捷键格式不正确，请使用类似 Alt+Q 的格式。",
        "floating_button_size": "悬浮按钮大小",
        "floating_button_size_help": "最小化后的圆形按钮大小，可按需要调小或调大。",
        "floating_button_color_preset": "亮起颜色预设",
        "floating_button_custom_color": "自定义颜色代码",
        "floating_button_color_help": "选择预设颜色，或选择“自定义”并输入 #RRGGBB 颜色代码。",
        "floating_button_color_invalid": "自定义颜色代码不正确，请使用类似 #cfefff 的格式。",
        "color_preset_blue": "浅蓝",
        "color_preset_green": "绿色",
        "color_preset_purple": "紫色",
        "color_preset_yellow": "黄色",
        "color_preset_pink": "粉色",
        "color_preset_white": "白色",
        "color_preset_custom": "自定义",
        "save_settings": "保存设置",
        "settings_error": "设置错误",
        "text_size_title": "翻译框文字大小",
        "interface_language_title": "软件界面显示语言",
        "interface_language_hint": "选择软件菜单、按钮和提示使用的语言。保存后重启软件会完整生效。",
        "input_font_size": "输入文字大小",
        "output_font_size": "译文文字大小",
        "back_font_size": "回翻译文字大小",
        "text_size_hint": "这里控制输入、翻译、回翻译三个文字区域的大小；系统界面文字会随窗口缩放自动变化。",
        "settings_saved": "设置已保存",
        "settings_saved_body": "设置已经保存并应用。界面显示语言会在下次启动时完整生效。",
        "input_required": "请输入需要翻译的文字",
        "same_language": "上下语言相同，请先切换其中一个语言",
        "translating": "正在翻译...",
        "listening": "正在听写，请对着默认麦克风说话...",
        "speaking": "正在使用默认扬声器朗读...",
        "done": "完成：{provider}",
        "failed": "翻译失败",
        "speech_failed": "语音功能失败",
        "speech_done": "语音输入完成",
        "speech_no_text": "没有可朗读的文字",
        "copied": "译文已复制",
        "pasted_external": "译文已输入到外部窗口",
        "sent_external": "译文已发送到外部窗口，输入框已清空",
        "direct_enabled": "直译已开启：在聊天输入框按 Enter 会翻译并替换；快捷键 {hotkey}",
        "direct_disabled": "直译已关闭；快捷键 {hotkey}",
        "direct_hotkey": "直译快捷键：{hotkey}",
        "direct_unavailable": "直译只支持 Windows 外部输入窗口",
        "direct_capturing": "正在读取聊天输入...",
        "direct_captured": "已读取外部输入，正在直译...",
        "direct_waiting": "正在直译，请稍等",
        "direct_ready": "直译完成，正在替换聊天框内容...",
        "direct_replaced": "已替换聊天框内容，再按 Enter 发送",
        "direct_sent": "直译消息已发送，输入框已清空",
        "direct_input_missing": "聊天输入框没有可直译的内容",
        "paste_target_missing": "没有找到外部输入窗口，已复制译文",
        "paste_failed": "输入到外部窗口失败，已复制译文",
        "no_output": "没有可复制的译文",
        "cleared": "已清空",
        "swapped": "已交换上下语言",
    },
    "en": {
        "app_title": "AI Translator",
        "ready": "Ready",
        "translate_tab": "Translate",
        "settings_tab": "Settings",
        "font_tab": "Text Size",
        "display_tab": "Interface",
        "text_tab": "Text",
        "direct_tab": "Direct",
        "swap_languages": "⇅ Swap Languages",
        "translate": "Translate",
        "copy_output": "Copy",
        "clear": "Clear",
        "listen_input": "Mic",
        "speak_input": "Speak Input",
        "speak_output": "Speak Translation",
        "back_translation": "Back Translation",
        "back_to": "Back to: {source}",
        "always_on_top": "Always keep window on top",
        "ui_language": "Interface language",
        "translation_method": "Translation Method",
        "ai_translate": "AI Translate",
        "google_translate": "Google Translate",
        "microsoft_translate": "Microsoft Translate",
        "microsoft_key": "Microsoft API KEY",
        "microsoft_region": "Microsoft region",
        "microsoft_key_help": "Used when Microsoft is selected for back translation. You can also set MICROSOFT_TRANSLATOR_KEY / MICROSOFT_TRANSLATOR_REGION.",
        "ai_platform": "AI Platform",
        "country": "Country context",
        "gender": "My gender",
        "gemini_key": "Gemini API KEY",
        "gemini_key_help": "Enter one key per line; the next key is tried if the current one fails.",
        "gemini_model": "Gemini Model",
        "groq_key": "Groq API KEY",
        "groq_key_help": "Groq also supports multi-line key rotation.",
        "groq_model": "Groq Model",
        "my_languages": "My Languages (up to 3)",
        "their_languages": "Other Languages (up to 3)",
        "back_setting": "Back Translation",
        "back_platform_setting": "Back-translation platform",
        "back_yes": "Yes, show the back-translation box",
        "back_no": "No, do not back-translate",
        "direct_settings": "Direct Mode Settings",
        "direct_hotkey_setting": "Direct mode shortcut",
        "direct_hotkey_help": "Use the same shortcut to turn Direct mode on or off. Examples: Alt+Q, Ctrl+Shift+T, Ctrl+Alt+D. Supports Ctrl / Alt / Shift plus letters, digits, or F1-F12.",
        "direct_hotkey_invalid": "Invalid direct shortcut. Use a format such as Alt+Q.",
        "floating_button_size": "Floating button size",
        "floating_button_size_help": "Adjust the circular button shown when the app is minimized.",
        "floating_button_color_preset": "Active color preset",
        "floating_button_custom_color": "Custom color code",
        "floating_button_color_help": "Choose a preset, or choose Custom and enter a #RRGGBB color code.",
        "floating_button_color_invalid": "Invalid custom color code. Use a format like #cfefff.",
        "color_preset_blue": "Light blue",
        "color_preset_green": "Green",
        "color_preset_purple": "Purple",
        "color_preset_yellow": "Yellow",
        "color_preset_pink": "Pink",
        "color_preset_white": "White",
        "color_preset_custom": "Custom",
        "save_settings": "Save Settings",
        "settings_error": "Settings Error",
        "text_size_title": "Translation Box Text Size",
        "interface_language_title": "Interface Language",
        "interface_language_hint": "Choose the language used by menus, buttons, and messages. Restart the app for the full interface to refresh.",
        "input_font_size": "Input text size",
        "output_font_size": "Translation text size",
        "back_font_size": "Back-translation text size",
        "text_size_hint": "These settings control the three text boxes. The rest of the interface scales automatically with the window.",
        "settings_saved": "Settings Saved",
        "settings_saved_body": "Settings have been saved and applied. The interface language fully applies after restart.",
        "input_required": "Enter text to translate",
        "same_language": "Source and target languages are the same.",
        "translating": "Translating...",
        "listening": "Listening through the default microphone...",
        "speaking": "Speaking through the default speaker...",
        "done": "Done: {provider}",
        "failed": "Translation failed",
        "speech_failed": "Speech failed",
        "speech_done": "Speech input complete",
        "speech_no_text": "No text to speak",
        "copied": "Translation copied",
        "pasted_external": "Translation pasted into the external window",
        "sent_external": "Translation sent to the external window; input cleared",
        "direct_enabled": "Direct mode is on: Enter in the chat input translates and replaces; shortcut {hotkey}",
        "direct_disabled": "Direct mode is off; shortcut {hotkey}",
        "direct_hotkey": "Direct shortcut: {hotkey}",
        "direct_unavailable": "Direct mode only supports Windows external input windows",
        "direct_capturing": "Reading the chat input...",
        "direct_captured": "External input captured, translating...",
        "direct_waiting": "Translating, please wait",
        "direct_ready": "Direct translation ready. Replacing the chat input...",
        "direct_replaced": "Chat input replaced. Press Enter again to send.",
        "direct_sent": "Direct message sent; input cleared",
        "direct_input_missing": "No text found in the chat input",
        "paste_target_missing": "No external input window found; translation copied",
        "paste_failed": "Could not paste into the external window; translation copied",
        "no_output": "Nothing to copy",
        "cleared": "Cleared",
        "swapped": "Languages swapped",
    },
    "ja": {
        "app_title": "AI 翻訳アシスタント",
        "ready": "準備完了",
        "translate_tab": "翻訳",
        "settings_tab": "設定",
        "font_tab": "文字サイズ",
        "display_tab": "表示言語",
        "text_tab": "文字",
        "direct_tab": "直訳",
        "swap_languages": "⇅ 言語を交換",
        "translate": "翻訳",
        "copy_output": "翻訳をコピー",
        "clear": "クリア",
        "back_translation": "逆翻訳",
        "back_to": "逆翻訳先：{source}",
        "always_on_top": "ウィンドウを常に最前面に表示",
        "ui_language": "画面表示言語",
        "translation_method": "翻訳方式",
        "ai_translate": "AI 翻訳",
        "google_translate": "Google 翻訳",
        "microsoft_translate": "Microsoft 翻訳",
        "microsoft_key": "Microsoft API KEY",
        "microsoft_region": "Microsoft リージョン",
        "microsoft_key_help": "逆翻訳で Microsoft を選ぶ場合に使用します。環境変数 MICROSOFT_TRANSLATOR_KEY / MICROSOFT_TRANSLATOR_REGION も使えます。",
        "ai_platform": "AI プラットフォーム",
        "country": "国の特徴",
        "gender": "自分の性別",
        "gemini_key": "Gemini API KEY",
        "gemini_key_help": "1行に1つのキーを入力。失敗すると次のキーを試します。",
        "gemini_model": "Gemini モデル",
        "groq_key": "Groq API KEY",
        "groq_key_help": "Groq も複数行キーの切り替えに対応しています。",
        "groq_model": "Groq モデル",
        "my_languages": "自分の言語（最大3つ）",
        "their_languages": "相手の言語（最大3つ）",
        "back_setting": "逆翻訳",
        "back_platform_setting": "逆翻訳プラットフォーム",
        "back_yes": "はい、逆翻訳欄を表示する",
        "back_no": "いいえ、逆翻訳しない",
        "save_settings": "設定を保存",
        "text_size_title": "翻訳欄の文字サイズ",
        "interface_language_title": "画面表示言語",
        "interface_language_hint": "メニュー、ボタン、メッセージの表示言語を選びます。完全な反映には再起動してください。",
        "input_font_size": "入力文字サイズ",
        "output_font_size": "翻訳文字サイズ",
        "back_font_size": "逆翻訳文字サイズ",
        "text_size_hint": "ここでは3つのテキスト欄の文字サイズを設定します。他の画面文字はウィンドウに合わせて自動調整されます。",
        "settings_saved": "設定を保存しました",
        "settings_saved_body": "設定を保存して適用しました。画面表示言語は次回起動時に完全に反映されます。",
        "input_required": "翻訳するテキストを入力してください",
        "same_language": "上下の言語が同じです。",
        "translating": "翻訳中...",
        "done": "完了：{provider}",
        "failed": "翻訳に失敗しました",
        "copied": "翻訳をコピーしました",
        "pasted_external": "外部ウィンドウに翻訳を入力しました",
        "sent_external": "外部ウィンドウへ送信し、入力欄をクリアしました",
        "paste_target_missing": "外部入力ウィンドウが見つかりません。翻訳をコピーしました",
        "paste_failed": "外部ウィンドウへの入力に失敗しました。翻訳をコピーしました",
        "no_output": "コピーできる翻訳がありません",
        "cleared": "クリアしました",
        "swapped": "言語を交換しました",
    },
}

UI_TEXT["zh-TW"] = {
    **UI_TEXT["zh-CN"],
    "app_title": "AI 翻譯助手",
    "ready": "準備就緒",
    "settings_tab": "設定",
    "font_tab": "文字大小",
    "display_tab": "介面語言",
    "text_tab": "文字",
    "direct_tab": "直譯",
    "direct_settings": "直譯設定",
    "direct_hotkey_setting": "啟動直譯快速鍵",
    "direct_hotkey_help": "同一個快速鍵可來回開啟/關閉直譯。格式範例：Alt+Q、Ctrl+Shift+T、Ctrl+Alt+D。支援 Ctrl / Alt / Shift 加字母、數字或 F1-F12。",
    "direct_hotkey_invalid": "直譯快速鍵格式不正確，請使用類似 Alt+Q 的格式。",
    "floating_button_size": "懸浮按鈕大小",
    "floating_button_size_help": "最小化後的圓形按鈕大小，可依需要調小或調大。",
    "floating_button_color_preset": "亮起顏色預設",
    "floating_button_custom_color": "自訂顏色代碼",
    "floating_button_color_help": "選擇預設顏色，或選擇「自訂」並輸入 #RRGGBB 顏色代碼。",
    "floating_button_color_invalid": "自訂顏色代碼不正確，請使用類似 #cfefff 的格式。",
    "color_preset_blue": "淺藍",
    "color_preset_green": "綠色",
    "color_preset_purple": "紫色",
    "color_preset_yellow": "黃色",
    "color_preset_pink": "粉色",
    "color_preset_white": "白色",
    "color_preset_custom": "自訂",
    "swap_languages": "⇅ 交換語言",
    "copy_output": "複製譯文",
    "back_translation": "回翻譯",
    "back_to": "回翻譯為：{source}",
    "always_on_top": "軟體介面永遠置頂",
    "ui_language": "軟體介面顯示語言",
    "interface_language_title": "軟體介面顯示語言",
    "interface_language_hint": "選擇軟體選單、按鈕和提示使用的語言。儲存後重新啟動會完整生效。",
    "translation_method": "翻譯方式",
    "google_translate": "Google 翻譯",
    "country": "國家特色",
    "gender": "我的性別",
    "my_languages": "我的語言（最多三種）",
    "their_languages": "對方語言（最多三種）",
    "back_yes": "是，顯示回翻譯小介面",
    "back_no": "否，不進行回翻譯",
    "text_size_title": "翻譯框文字大小",
    "input_font_size": "輸入文字大小",
    "output_font_size": "譯文文字大小",
    "back_font_size": "回翻譯文字大小",
    "settings_saved": "設定已儲存",
    "settings_saved_body": "設定已儲存並套用。介面顯示語言會在下次啟動時完整生效。",
    "input_required": "請輸入需要翻譯的文字",
    "same_language": "上下語言相同，請先切換其中一個語言",
    "translating": "正在翻譯...",
    "failed": "翻譯失敗",
    "copied": "譯文已複製",
    "no_output": "沒有可複製的譯文",
    "cleared": "已清空",
    "swapped": "已交換上下語言",
}

UI_TEXT["ko"] = {
    **UI_TEXT["en"],
    "app_title": "AI 번역 도우미",
    "ready": "준비됨",
    "translate_tab": "번역",
    "settings_tab": "설정",
    "font_tab": "글자 크기",
    "display_tab": "인터페이스",
    "swap_languages": "⇅ 언어 교환",
    "translate": "번역",
    "copy_output": "번역 복사",
    "clear": "지우기",
    "back_translation": "역번역",
    "back_to": "역번역 대상: {source}",
    "always_on_top": "창을 항상 위에 표시",
    "ui_language": "인터페이스 언어",
    "interface_language_title": "인터페이스 언어",
    "interface_language_hint": "메뉴, 버튼, 메시지에 사용할 언어를 선택하세요. 전체 적용은 앱 재시작 후 반영됩니다.",
    "translation_method": "번역 방식",
    "ai_translate": "AI 번역",
    "google_translate": "Google 번역",
    "ai_platform": "AI 플랫폼",
    "country": "국가/지역 맥락",
    "gender": "내 성별",
    "my_languages": "내 언어(최대 3개)",
    "their_languages": "상대 언어(최대 3개)",
    "back_setting": "역번역",
    "back_yes": "예, 역번역 창 표시",
    "back_no": "아니요, 역번역 안 함",
    "save_settings": "설정 저장",
    "text_size_title": "번역창 글자 크기",
    "input_font_size": "입력 글자 크기",
    "output_font_size": "번역 글자 크기",
    "back_font_size": "역번역 글자 크기",
    "settings_saved": "설정 저장됨",
    "input_required": "번역할 텍스트를 입력하세요",
    "translating": "번역 중...",
    "failed": "번역 실패",
    "copied": "번역을 복사했습니다",
    "cleared": "지웠습니다",
}

UI_TEXT["fr"] = {
    **UI_TEXT["en"],
    "app_title": "Assistant de traduction IA",
    "ready": "Prêt",
    "translate_tab": "Traduire",
    "settings_tab": "Réglages",
    "font_tab": "Taille du texte",
    "display_tab": "Interface",
    "swap_languages": "⇅ Échanger les langues",
    "translate": "Traduire",
    "copy_output": "Copier",
    "clear": "Effacer",
    "back_translation": "Rétro-traduction",
    "back_to": "Retour vers : {source}",
    "always_on_top": "Toujours au premier plan",
    "ui_language": "Langue de l’interface",
    "interface_language_title": "Langue de l’interface",
    "interface_language_hint": "Choisissez la langue des menus, boutons et messages. Redémarrez l’application pour l’appliquer entièrement.",
    "translation_method": "Mode de traduction",
    "ai_translate": "Traduction IA",
    "google_translate": "Google Traduction",
    "ai_platform": "Plateforme IA",
    "country": "Contexte pays",
    "gender": "Mon genre",
    "my_languages": "Mes langues (3 max.)",
    "their_languages": "Langues de l’autre personne (3 max.)",
    "back_setting": "Rétro-traduction",
    "back_yes": "Oui, afficher la rétro-traduction",
    "back_no": "Non, ne pas rétro-traduire",
    "save_settings": "Enregistrer",
    "text_size_title": "Taille du texte des zones",
    "input_font_size": "Taille du texte saisi",
    "output_font_size": "Taille de la traduction",
    "back_font_size": "Taille de la rétro-traduction",
    "settings_saved": "Réglages enregistrés",
    "input_required": "Saisissez le texte à traduire",
    "translating": "Traduction...",
    "failed": "Échec de la traduction",
    "copied": "Traduction copiée",
    "cleared": "Effacé",
}

UI_TEXT["de"] = {
    **UI_TEXT["en"],
    "app_title": "KI-Übersetzungsassistent",
    "ready": "Bereit",
    "translate_tab": "Übersetzen",
    "settings_tab": "Einstellungen",
    "font_tab": "Textgröße",
    "display_tab": "Oberfläche",
    "swap_languages": "⇅ Sprachen tauschen",
    "translate": "Übersetzen",
    "copy_output": "Kopieren",
    "clear": "Leeren",
    "back_translation": "Rückübersetzung",
    "back_to": "Zurück nach: {source}",
    "always_on_top": "Fenster immer im Vordergrund",
    "ui_language": "Sprache der Oberfläche",
    "interface_language_title": "Sprache der Oberfläche",
    "interface_language_hint": "Wählen Sie die Sprache für Menüs, Schaltflächen und Meldungen. Starten Sie die App neu, damit alles übernommen wird.",
    "translation_method": "Übersetzungsmethode",
    "ai_translate": "KI-Übersetzung",
    "google_translate": "Google Übersetzer",
    "ai_platform": "KI-Plattform",
    "country": "Länderkontext",
    "gender": "Mein Geschlecht",
    "save_settings": "Speichern",
    "text_size_title": "Textgröße der Übersetzungsfelder",
    "input_font_size": "Eingabetextgröße",
    "output_font_size": "Übersetzungstextgröße",
    "back_font_size": "Rückübersetzungstextgröße",
    "settings_saved": "Einstellungen gespeichert",
    "input_required": "Text zum Übersetzen eingeben",
    "translating": "Übersetzen...",
    "failed": "Übersetzung fehlgeschlagen",
    "copied": "Übersetzung kopiert",
    "cleared": "Geleert",
}

UI_TEXT["es"] = {
    **UI_TEXT["en"],
    "app_title": "Asistente de traducción IA",
    "ready": "Listo",
    "translate_tab": "Traducir",
    "settings_tab": "Ajustes",
    "font_tab": "Tamaño de texto",
    "display_tab": "Interfaz",
    "swap_languages": "⇅ Intercambiar idiomas",
    "translate": "Traducir",
    "copy_output": "Copiar",
    "clear": "Borrar",
    "back_translation": "Retraducción",
    "back_to": "Retraducir a: {source}",
    "always_on_top": "Mantener ventana siempre arriba",
    "ui_language": "Idioma de la interfaz",
    "interface_language_title": "Idioma de la interfaz",
    "interface_language_hint": "Elige el idioma de menús, botones y mensajes. Reinicia la aplicación para aplicarlo por completo.",
    "translation_method": "Método de traducción",
    "ai_translate": "Traducción IA",
    "google_translate": "Google Traductor",
    "ai_platform": "Plataforma IA",
    "country": "Contexto del país",
    "gender": "Mi género",
    "save_settings": "Guardar",
    "text_size_title": "Tamaño del texto",
    "input_font_size": "Tamaño del texto de entrada",
    "output_font_size": "Tamaño del texto traducido",
    "back_font_size": "Tamaño de la retraducción",
    "settings_saved": "Ajustes guardados",
    "input_required": "Introduce texto para traducir",
    "translating": "Traduciendo...",
    "failed": "Error de traducción",
    "copied": "Traducción copiada",
    "cleared": "Borrado",
}

UI_TEXT["ru"] = {
    **UI_TEXT["en"],
    "app_title": "AI помощник перевода",
    "ready": "Готово",
    "translate_tab": "Перевод",
    "settings_tab": "Настройки",
    "font_tab": "Размер текста",
    "display_tab": "Интерфейс",
    "swap_languages": "⇅ Поменять языки",
    "translate": "Перевести",
    "copy_output": "Копировать",
    "clear": "Очистить",
    "back_translation": "Обратный перевод",
    "back_to": "Обратно на: {source}",
    "always_on_top": "Окно всегда поверх остальных",
    "ui_language": "Язык интерфейса",
    "interface_language_title": "Язык интерфейса",
    "interface_language_hint": "Выберите язык меню, кнопок и сообщений. Перезапустите приложение для полного применения.",
    "translation_method": "Способ перевода",
    "ai_translate": "AI перевод",
    "google_translate": "Google перевод",
    "ai_platform": "AI платформа",
    "country": "Контекст страны",
    "gender": "Мой пол",
    "save_settings": "Сохранить",
    "text_size_title": "Размер текста в полях",
    "input_font_size": "Размер ввода",
    "output_font_size": "Размер перевода",
    "back_font_size": "Размер обратного перевода",
    "settings_saved": "Настройки сохранены",
    "input_required": "Введите текст для перевода",
    "translating": "Перевод...",
    "failed": "Ошибка перевода",
    "copied": "Перевод скопирован",
    "cleared": "Очищено",
}

EXTRA_UI_TEXT = {
    "it": {
        "app_title": "Assistente traduttore AI",
        "ready": "Pronto",
        "translate_tab": "Traduci",
        "settings_tab": "Impostazioni",
        "font_tab": "Dimensione testo",
        "display_tab": "Interfaccia",
        "translate": "Traduci",
        "copy_output": "Copia",
        "clear": "Cancella",
        "ui_language": "Lingua interfaccia",
        "interface_language_title": "Lingua interfaccia",
        "interface_language_hint": "Scegli la lingua di menu, pulsanti e messaggi. Riavvia per applicarla completamente.",
        "save_settings": "Salva",
    },
    "pt": {
        "app_title": "Assistente de tradução AI",
        "ready": "Pronto",
        "translate_tab": "Traduzir",
        "settings_tab": "Definições",
        "font_tab": "Tamanho do texto",
        "display_tab": "Interface",
        "translate": "Traduzir",
        "copy_output": "Copiar",
        "clear": "Limpar",
        "ui_language": "Idioma da interface",
        "interface_language_title": "Idioma da interface",
        "interface_language_hint": "Escolha o idioma de menus, botões e mensagens. Reinicie para aplicar tudo.",
        "save_settings": "Guardar",
    },
    "ar": {
        "app_title": "مساعد الترجمة بالذكاء الاصطناعي",
        "ready": "جاهز",
        "translate_tab": "ترجمة",
        "settings_tab": "الإعدادات",
        "font_tab": "حجم النص",
        "display_tab": "الواجهة",
        "translate": "ترجمة",
        "copy_output": "نسخ",
        "clear": "مسح",
        "ui_language": "لغة الواجهة",
        "interface_language_title": "لغة الواجهة",
        "interface_language_hint": "اختر لغة القوائم والأزرار والرسائل. أعد تشغيل التطبيق للتطبيق الكامل.",
        "save_settings": "حفظ",
    },
    "hi": {
        "app_title": "AI अनुवाद सहायक",
        "ready": "तैयार",
        "translate_tab": "अनुवाद",
        "settings_tab": "सेटिंग",
        "font_tab": "टेक्स्ट आकार",
        "display_tab": "इंटरफेस",
        "translate": "अनुवाद",
        "copy_output": "कॉपी",
        "clear": "साफ करें",
        "ui_language": "इंटरफेस भाषा",
        "interface_language_title": "इंटरफेस भाषा",
        "interface_language_hint": "मेनू, बटन और संदेशों की भाषा चुनें। पूरा बदलाव देखने के लिए ऐप फिर खोलें।",
        "save_settings": "सहेजें",
    },
    "ne": {
        "app_title": "AI अनुवाद सहायक",
        "ready": "तयार",
        "translate_tab": "अनुवाद",
        "settings_tab": "सेटिङ",
        "font_tab": "पाठ आकार",
        "display_tab": "इन्टरफेस",
        "translate": "अनुवाद",
        "copy_output": "प्रतिलिपि",
        "clear": "खाली",
        "ui_language": "इन्टरफेस भाषा",
        "interface_language_title": "इन्टरफेस भाषा",
        "interface_language_hint": "मेनु, बटन र सन्देशको भाषा छान्नुहोस्। पूर्ण लागू गर्न एप पुनः खोल्नुहोस्।",
        "save_settings": "सुरक्षित",
    },
    "my": {
        "app_title": "AI ဘာသာပြန် ကူညီသူ",
        "ready": "အသင့်",
        "translate_tab": "ဘာသာပြန်",
        "settings_tab": "ဆက်တင်",
        "font_tab": "စာလုံးအရွယ်",
        "display_tab": "မျက်နှာပြင်",
        "translate": "ဘာသာပြန်",
        "copy_output": "ကူးယူ",
        "clear": "ရှင်း",
        "ui_language": "မျက်နှာပြင်ဘာသာ",
        "interface_language_title": "မျက်နှာပြင်ဘာသာစကား",
        "interface_language_hint": "မီနူး၊ ခလုတ်နှင့် စာသားများအတွက် ဘာသာစကားကို ရွေးပါ။ အပြည့်အစုံပြောင်းရန် ပြန်ဖွင့်ပါ။",
        "save_settings": "သိမ်း",
    },
    "th": {
        "app_title": "ผู้ช่วยแปล AI",
        "ready": "พร้อม",
        "translate_tab": "แปล",
        "settings_tab": "ตั้งค่า",
        "font_tab": "ขนาดตัวอักษร",
        "display_tab": "ภาษา UI",
        "translate": "แปล",
        "copy_output": "คัดลอก",
        "clear": "ล้าง",
        "ui_language": "ภาษาอินเทอร์เฟซ",
        "interface_language_title": "ภาษาอินเทอร์เฟซ",
        "interface_language_hint": "เลือกภาษาของเมนู ปุ่ม และข้อความ รีสตาร์ทเพื่อให้มีผลครบถ้วน",
        "save_settings": "บันทึก",
    },
    "vi": {
        "app_title": "Trợ lý dịch AI",
        "ready": "Sẵn sàng",
        "translate_tab": "Dịch",
        "settings_tab": "Cài đặt",
        "font_tab": "Cỡ chữ",
        "display_tab": "Giao diện",
        "translate": "Dịch",
        "copy_output": "Sao chép",
        "clear": "Xóa",
        "ui_language": "Ngôn ngữ giao diện",
        "interface_language_title": "Ngôn ngữ giao diện",
        "interface_language_hint": "Chọn ngôn ngữ menu, nút và thông báo. Khởi động lại để áp dụng đầy đủ.",
        "save_settings": "Lưu",
    },
    "id": {
        "app_title": "Asisten Terjemahan AI",
        "ready": "Siap",
        "translate_tab": "Terjemah",
        "settings_tab": "Pengaturan",
        "font_tab": "Ukuran teks",
        "display_tab": "Antarmuka",
        "translate": "Terjemah",
        "copy_output": "Salin",
        "clear": "Hapus",
        "ui_language": "Bahasa antarmuka",
        "interface_language_title": "Bahasa antarmuka",
        "interface_language_hint": "Pilih bahasa menu, tombol, dan pesan. Mulai ulang agar seluruh tampilan berubah.",
        "save_settings": "Simpan",
    },
    "nl": {
        "app_title": "AI vertaalassistent",
        "ready": "Gereed",
        "translate_tab": "Vertalen",
        "settings_tab": "Instellingen",
        "font_tab": "Tekstgrootte",
        "display_tab": "Interface",
        "translate": "Vertalen",
        "copy_output": "Kopiëren",
        "clear": "Wissen",
        "ui_language": "Interfacetaal",
        "interface_language_title": "Interfacetaal",
        "interface_language_hint": "Kies de taal voor menu's, knoppen en meldingen. Herstart voor volledige toepassing.",
        "save_settings": "Opslaan",
    },
    "pl": {
        "app_title": "Asystent tłumaczenia AI",
        "ready": "Gotowe",
        "translate_tab": "Tłumacz",
        "settings_tab": "Ustawienia",
        "font_tab": "Rozmiar tekstu",
        "display_tab": "Interfejs",
        "translate": "Tłumacz",
        "copy_output": "Kopiuj",
        "clear": "Wyczyść",
        "ui_language": "Język interfejsu",
        "interface_language_title": "Język interfejsu",
        "interface_language_hint": "Wybierz język menu, przycisków i komunikatów. Uruchom ponownie, aby zastosować w pełni.",
        "save_settings": "Zapisz",
    },
    "tr": {
        "app_title": "AI Çeviri Asistanı",
        "ready": "Hazır",
        "translate_tab": "Çevir",
        "settings_tab": "Ayarlar",
        "font_tab": "Metin boyutu",
        "display_tab": "Arayüz",
        "translate": "Çevir",
        "copy_output": "Kopyala",
        "clear": "Temizle",
        "ui_language": "Arayüz dili",
        "interface_language_title": "Arayüz dili",
        "interface_language_hint": "Menü, düğme ve iletilerin dilini seçin. Tam uygulama için yeniden başlatın.",
        "save_settings": "Kaydet",
    },
    "sv": {
        "app_title": "AI-översättningsassistent",
        "ready": "Redo",
        "translate_tab": "Översätt",
        "settings_tab": "Inställningar",
        "font_tab": "Textstorlek",
        "display_tab": "Gränssnitt",
        "translate": "Översätt",
        "copy_output": "Kopiera",
        "clear": "Rensa",
        "ui_language": "Gränssnittsspråk",
        "interface_language_title": "Gränssnittsspråk",
        "interface_language_hint": "Välj språk för menyer, knappar och meddelanden. Starta om för full effekt.",
        "save_settings": "Spara",
    },
    "uk": {
        "app_title": "AI помічник перекладу",
        "ready": "Готово",
        "translate_tab": "Переклад",
        "settings_tab": "Налаштування",
        "font_tab": "Розмір тексту",
        "display_tab": "Інтерфейс",
        "translate": "Перекласти",
        "copy_output": "Копіювати",
        "clear": "Очистити",
        "ui_language": "Мова інтерфейсу",
        "interface_language_title": "Мова інтерфейсу",
        "interface_language_hint": "Виберіть мову меню, кнопок і повідомлень. Перезапустіть застосунок для повного оновлення.",
        "save_settings": "Зберегти",
    },
    "el": {
        "app_title": "Βοηθός μετάφρασης AI",
        "ready": "Έτοιμο",
        "translate_tab": "Μετάφραση",
        "settings_tab": "Ρυθμίσεις",
        "font_tab": "Μέγεθος κειμένου",
        "display_tab": "Διεπαφή",
        "translate": "Μετάφραση",
        "copy_output": "Αντιγραφή",
        "clear": "Καθαρισμός",
        "ui_language": "Γλώσσα διεπαφής",
        "interface_language_title": "Γλώσσα διεπαφής",
        "interface_language_hint": "Επιλέξτε γλώσσα για μενού, κουμπιά και μηνύματα. Κάντε επανεκκίνηση για πλήρη εφαρμογή.",
        "save_settings": "Αποθήκευση",
    },
    "he": {
        "app_title": "עוזר תרגום AI",
        "ready": "מוכן",
        "translate_tab": "תרגום",
        "settings_tab": "הגדרות",
        "font_tab": "גודל טקסט",
        "display_tab": "ממשק",
        "translate": "תרגם",
        "copy_output": "העתק",
        "clear": "נקה",
        "ui_language": "שפת ממשק",
        "interface_language_title": "שפת ממשק",
        "interface_language_hint": "בחר שפה לתפריטים, כפתורים והודעות. הפעל מחדש כדי להחיל באופן מלא.",
        "save_settings": "שמור",
    },
}

for code, text in EXTRA_UI_TEXT.items():
    UI_TEXT[code] = {**UI_TEXT["en"], **text}

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-3.1-flash-lite-preview",
]

GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

DEFAULT_CONFIG = {
    "always_on_top": False,
    "ui_language": "zh-CN",
    "translation_mode": "google",
    "use_ai": False,
    "ai_provider": "gemini",
    "gemini_keys": "",
    "groq_keys": "",
    "gemini_model": "gemini-2.0-flash",
    "groq_model": "llama-3.3-70b-versatile",
    "translation_platform": "Google",
    "back_platform": "Google",
    "microsoft_key": "",
    "microsoft_region": "",
    "my_languages": ["en", "zh-CN", "ja"],
    "their_languages": ["zh-CN", "en", "ja"],
    "source_lang": "en",
    "target_lang": "zh-CN",
    "country": "",
    "gender": "不指定",
    "back_translate": True,
    "input_font_size": 13,
    "output_font_size": 13,
    "back_font_size": 11,
    "window_size": "700x540",
    "direct_hotkey": "Alt+Q",
    "floating_position": "",
    "floating_button_size": 54,
    "floating_active_color_preset": "blue",
    "floating_active_color": FLOAT_ACTIVE_COLOR,
}


@dataclass
class TranslationResult:
    text: str
    back_text: str
    provider: str
    warning: str = ""


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

    config = DEFAULT_CONFIG.copy()
    config.update({key: value for key, value in data.items() if key in config})
    if config.get("translation_mode") not in ("ai", "google"):
        config["translation_mode"] = "ai" if config.get("use_ai") else "google"
    config["use_ai"] = config.get("translation_mode") == "ai"
    if config.get("ai_provider") not in ("gemini", "groq"):
        config["ai_provider"] = "gemini"
    if config.get("ui_language") not in UI_LANGUAGE_NAMES:
        config["ui_language"] = "zh-CN"
    for size_key, default_size in (
        ("input_font_size", 13),
        ("output_font_size", 13),
        ("back_font_size", 11),
    ):
        try:
            config[size_key] = min(32, max(8, int(config.get(size_key, default_size))))
        except (TypeError, ValueError):
            config[size_key] = default_size
    config["window_size"] = normalize_window_size(config.get("window_size"), DEFAULT_CONFIG["window_size"])
    raw_direct_hotkey = config.get("direct_hotkey")
    if raw_direct_hotkey in (None, "", "Ctrl+Alt+D"):
        raw_direct_hotkey = DEFAULT_CONFIG["direct_hotkey"]
    elif normalize_direct_hotkey(raw_direct_hotkey, DEFAULT_CONFIG["direct_hotkey"]) == "Ctrl+Alt+D":
        raw_direct_hotkey = DEFAULT_CONFIG["direct_hotkey"]
    config["direct_hotkey"] = normalize_direct_hotkey(raw_direct_hotkey, DEFAULT_CONFIG["direct_hotkey"])
    config["floating_button_size"] = normalize_floating_button_size(
        config.get("floating_button_size"), DEFAULT_CONFIG["floating_button_size"]
    )
    color_preset = config.get("floating_active_color_preset")
    if color_preset not in FLOAT_COLOR_PRESETS:
        color_preset = DEFAULT_CONFIG["floating_active_color_preset"]
    config["floating_active_color_preset"] = color_preset
    if color_preset == "custom":
        config["floating_active_color"] = normalize_hex_color(
            config.get("floating_active_color"), DEFAULT_CONFIG["floating_active_color"]
        )
    else:
        config["floating_active_color"] = FLOAT_COLOR_PRESETS[color_preset][0]
    config["my_languages"] = normalize_language_list(config.get("my_languages"), DEFAULT_CONFIG["my_languages"])
    config["their_languages"] = normalize_language_list(config.get("their_languages"), DEFAULT_CONFIG["their_languages"])

    if config.get("source_lang") not in LANGUAGE_NAMES:
        config["source_lang"] = config["my_languages"][0]
    if config.get("target_lang") not in LANGUAGE_NAMES:
        config["target_lang"] = config["their_languages"][0]
    return config


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def normalize_window_size(value, fallback: str = "700x540") -> str:
    if not isinstance(value, str):
        return fallback
    match = re.fullmatch(r"\s*(\d{3,4})x(\d{3,4})\s*", value)
    if not match:
        return fallback
    width = max(330, min(2400, int(match.group(1))))
    height = max(240, min(1800, int(match.group(2))))
    return f"{width}x{height}"


def normalize_floating_button_size(value, fallback: int = 54) -> int:
    try:
        return min(120, max(36, int(value)))
    except (TypeError, ValueError):
        return fallback


def normalize_hex_color(value, fallback: str = FLOAT_ACTIVE_COLOR) -> str:
    if not isinstance(value, str):
        return fallback
    color = value.strip()
    if not color:
        return fallback
    if not color.startswith("#"):
        color = f"#{color}"
    if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return color.lower()
    return fallback


def is_hex_color(value) -> bool:
    if not isinstance(value, str):
        return False
    color = value.strip()
    if not color.startswith("#"):
        color = f"#{color}"
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", color))


def parse_direct_hotkey(value) -> tuple[tuple[str, ...], int, str] | None:
    if not isinstance(value, str):
        return None
    parts = [part.strip() for part in value.split("+") if part.strip()]
    if len(parts) < 2:
        return None

    modifiers: set[str] = set()
    key_name = ""
    for part in parts:
        token = part.upper()
        if token in HOTKEY_MODIFIER_ALIASES:
            modifiers.add(HOTKEY_MODIFIER_ALIASES[token])
            continue
        if key_name:
            return None
        if token in HOTKEY_KEY_TO_VK:
            key_name = token
        else:
            return None

    if not modifiers or not key_name:
        return None

    ordered_modifiers = tuple(modifier for modifier in HOTKEY_MODIFIER_ORDER if modifier in modifiers)
    label = "+".join((*ordered_modifiers, key_name))
    return ordered_modifiers, HOTKEY_KEY_TO_VK[key_name], label


def normalize_direct_hotkey(value, fallback: str = "Alt+Q") -> str:
    parsed = parse_direct_hotkey(value)
    if parsed:
        return parsed[2]
    fallback_parsed = parse_direct_hotkey(fallback)
    return fallback_parsed[2] if fallback_parsed else "Alt+Q"


def normalize_language_list(value, fallback: list[str]) -> list[str]:
    result = []
    if isinstance(value, list):
        for code in value:
            if code in LANGUAGE_NAMES and code not in result:
                result.append(code)

    for code in fallback:
        if len(result) >= 3:
            break
        if code in LANGUAGE_NAMES and code not in result:
            result.append(code)

    return result[:3]


def api_keys(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def clean_http_error(code: int, detail: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", detail or "")
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if code == 429:
        return (
            "Google 翻译请求被临时限制（HTTP 429）。"
            "请稍后再试，或者在设置里切换到 AI 翻译 / Microsoft 翻译。"
        )
    if cleaned:
        return f"HTTP {code}: {cleaned[:260]}"
    return f"HTTP {code}: 翻译服务暂时不可用。"


def read_http_text(url: str, payload: object | None = None, headers: dict | None = None, timeout: int = 30) -> str:
    data = None
    request_headers = {"User-Agent": "AI-Translator-App/1.0"}
    if headers:
        request_headers.update(headers)

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=request_headers)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(clean_http_error(exc.code, detail)) from exc
    except URLError as exc:
        raise RuntimeError(f"网络连接失败：{exc.reason}") from exc


def read_http_json(url: str, payload: object | None = None, headers: dict | None = None, timeout: int = 30):
    body = read_http_text(url, payload=payload, headers=headers, timeout=timeout)
    return json.loads(body)


def speech_culture(language_code: str) -> str:
    return SPEECH_CULTURES.get(language_code, language_code)


def _powershell_base64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def clean_powershell_error(detail: str) -> str:
    detail = detail.strip()
    if detail.startswith("#< CLIXML"):
        parts = re.findall(r'<S S="Error">(.*?)</S>', detail, flags=re.DOTALL)
        detail = "\n".join(parts) if parts else detail

    detail = detail.replace("_x000D__x000A_", "\n").replace("_x000A_", "\n").replace("_x000D_", "\r")
    detail = re.sub(r"<[^>]+>", " ", detail)
    detail = unescape(detail)
    detail = re.sub(r"\s+", " ", detail).strip()

    if "Windows 语音识别包" in detail and "没有安装" in detail:
        culture_match = re.search(r"没有安装\s+([A-Za-z]{2,3}(?:-[A-Za-z0-9]+)?)\s+的 Windows 语音识别包", detail)
        culture = culture_match.group(1) if culture_match else "当前语言"
        return (
            f"系统没有安装 {culture} 的 Windows 语音识别包。"
            "请在 Windows 设置 > 时间和语言 > 语言和区域 中为该语言添加“语音识别”，"
            "或者先切换到已经安装语音识别的输入语言。"
        )
    return detail or "Windows 语音服务执行失败。"


def run_powershell_script(script: str, timeout: int = 30) -> str:
    if not IS_WINDOWS:
        raise RuntimeError("当前语音功能仅支持 Windows。")

    script = (
        "$ProgressPreference = 'SilentlyContinue'\n"
        "$ErrorActionPreference = 'Stop'\n"
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
        + script
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-STA",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(clean_powershell_error(detail))
    return completed.stdout.strip()


def recognize_speech(language_code: str, seconds: int = 8) -> str:
    culture_b64 = _powershell_base64(speech_culture(language_code))
    script = f"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$cultureName = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{culture_b64}'))
$culture = [System.Globalization.CultureInfo]::GetCultureInfo($cultureName)
$recognizer = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() |
    Where-Object {{ $_.Culture.Name -eq $culture.Name -or $_.Culture.TwoLetterISOLanguageName -eq $culture.TwoLetterISOLanguageName }} |
    Select-Object -First 1
if ($null -eq $recognizer) {{
    throw "没有安装 $cultureName 的 Windows 语音识别包。请在系统语言设置里添加该语言的语音识别。"
}}
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine $recognizer
try {{
    $engine.SetInputToDefaultAudioDevice()
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $engine.LoadGrammar($grammar)
    $result = $engine.Recognize([TimeSpan]::FromSeconds({int(seconds)}))
    if ($null -eq $result -or [string]::IsNullOrWhiteSpace($result.Text)) {{
        throw "没有识别到语音。"
    }}
    Write-Output $result.Text
}} finally {{
    $engine.Dispose()
}}
"""
    return run_powershell_script(script, timeout=seconds + 8).strip()


def speak_text(text: str, language_code: str) -> None:
    text_b64 = _powershell_base64(text)
    culture_b64 = _powershell_base64(speech_culture(language_code))
    script = f"""
Add-Type -AssemblyName System.Speech
$text = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text_b64}'))
$cultureName = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{culture_b64}'))
$culture = [System.Globalization.CultureInfo]::GetCultureInfo($cultureName)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
    $synth.SetOutputToDefaultAudioDevice()
    $voice = $synth.GetInstalledVoices() |
        Where-Object {{
            $_.Enabled -and ($_.VoiceInfo.Culture.Name -eq $culture.Name -or $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq $culture.TwoLetterISOLanguageName)
        }} |
        Select-Object -First 1
    if ($null -ne $voice) {{
        $synth.SelectVoice($voice.VoiceInfo.Name)
    }}
    $synth.Volume = 100
    $synth.Rate = 0
    $synth.Speak($text)
}} finally {{
    $synth.Dispose()
}}
"""
    run_powershell_script(script, timeout=max(20, min(120, len(text) // 8 + 20)))


GOOGLE_LANGUAGE_MAP = {
    "pt-BR": "pt",
    "pt-PT": "pt",
}


def google_language_code(language_code: str) -> str:
    return GOOGLE_LANGUAGE_MAP.get(language_code, language_code)


class GoogleMobileResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "").split()
        if tag == "div" and "result-container" in classes:
            self._depth = 1
        elif self._depth:
            self._depth += 1

    def handle_endtag(self, tag):
        if self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if self._depth and data:
            self.parts.append(data)

    @property
    def result(self) -> str:
        return unescape("".join(self.parts)).strip()


def google_translate_api(text: str, source_lang: str, target_lang: str, host: str) -> str:
    params = parse.urlencode(
        {
            "client": "gtx",
            "sl": google_language_code(source_lang),
            "tl": google_language_code(target_lang),
            "dt": "t",
            "q": text,
        }
    )
    data = read_http_json(f"https://{host}/translate_a/single?{params}", timeout=20)
    parts = data[0] if data and isinstance(data, list) else []
    translated = "".join(part[0] for part in parts if part and part[0])
    if not translated:
        raise RuntimeError("Google 翻译没有返回内容")
    return translated


def google_translate_mobile(text: str, source_lang: str, target_lang: str) -> str:
    params = parse.urlencode(
        {
            "sl": google_language_code(source_lang),
            "tl": google_language_code(target_lang),
            "q": text,
        }
    )
    body = read_http_text(
        f"https://translate.google.com/m?{params}",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
        timeout=20,
    )
    parser = GoogleMobileResultParser()
    parser.feed(body)
    if not parser.result:
        raise RuntimeError("Google 翻译备用接口没有返回内容")
    return parser.result


def google_translate(text: str, source_lang: str, target_lang: str) -> str:
    errors = []
    for host in ("translate.googleapis.com", "translate.google.com"):
        try:
            return google_translate_api(text, source_lang, target_lang, host)
        except Exception as exc:
            errors.append(str(exc))

    try:
        return google_translate_mobile(text, source_lang, target_lang)
    except Exception as exc:
        errors.append(str(exc))

    if any("HTTP 429" in error for error in errors):
        raise RuntimeError(
            "Google 翻译现在被临时限制（HTTP 429）。"
            "请稍后再试，或在设置里切换到 AI 翻译 / Microsoft 翻译。"
        )
    raise RuntimeError("Google 翻译失败：" + "；".join(errors[-2:]))


def google_translate_with_fallback(text: str, source_lang: str, target_lang: str, config: dict | None = None) -> tuple[str, str]:
    try:
        return google_translate(text, source_lang, target_lang), "Google"
    except Exception as google_error:
        config = config or {}
        if (config.get("microsoft_key") or os.environ.get("MICROSOFT_TRANSLATOR_KEY") or "").strip():
            try:
                return microsoft_translate(text, source_lang, target_lang, config), "Google 失败，已改用 Microsoft"
            except Exception:
                pass
        raise google_error


MICROSOFT_LANGUAGE_MAP = {
    "zh-CN": "zh-Hans",
    "zh-TW": "zh-Hant",
    "pt-BR": "pt",
    "pt-PT": "pt",
    "tl": "fil",
}


def microsoft_language_code(language_code: str) -> str:
    return MICROSOFT_LANGUAGE_MAP.get(language_code, language_code)


def microsoft_translate(text: str, source_lang: str, target_lang: str, config: dict | None = None) -> str:
    config = config or {}
    key = (config.get("microsoft_key") or os.environ.get("MICROSOFT_TRANSLATOR_KEY") or "").strip()
    region = (config.get("microsoft_region") or os.environ.get("MICROSOFT_TRANSLATOR_REGION") or "").strip()
    if not key:
        raise RuntimeError("Microsoft 回翻译需要 Microsoft Translator API KEY。请在设置页填写，或设置 MICROSOFT_TRANSLATOR_KEY 环境变量。")

    params = parse.urlencode(
        {
            "api-version": "3.0",
            "from": microsoft_language_code(source_lang),
            "to": microsoft_language_code(target_lang),
        }
    )
    headers = {
        "Accept": "application/json",
        "Ocp-Apim-Subscription-Key": key,
    }
    if region:
        headers["Ocp-Apim-Subscription-Region"] = region

    data = read_http_json(
        f"https://api.cognitive.microsofttranslator.com/translate?{params}",
        payload=[{"Text": text}],
        headers=headers,
        timeout=20,
    )
    translations = data[0].get("translations", []) if data and isinstance(data, list) else []
    translated = translations[0].get("text", "").strip() if translations else ""
    if not translated:
        raise RuntimeError("Microsoft 翻译没有返回内容")
    return translated


def regular_translate(text: str, source_lang: str, target_lang: str, platform: str = "Google", config: dict | None = None) -> tuple[str, str]:
    if platform == "Microsoft":
        return microsoft_translate(text, source_lang, target_lang, config), "Microsoft"
    return google_translate_with_fallback(text, source_lang, target_lang, config)


def translation_prompt(text: str, source_lang: str, target_lang: str, config: dict, back_translate: bool = False) -> str:
    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    country = config.get("country", "").strip() or "未指定"
    gender = config.get("gender", "不指定")
    purpose = "This is a back translation for checking meaning." if back_translate else "This is a direct translation."
    return (
        f"{purpose}\n"
        f"Translate from {source_name} to {target_name}.\n"
        f"Country or regional context: {country}.\n"
        f"Speaker gender: {gender}.\n"
        "If the target language uses grammatical gender, honorifics, or regional wording, choose forms that match the context.\n"
        "Return only the translated text. Do not add explanations, labels, markdown, or quotes.\n\n"
        "Text:\n"
        f"{text}"
    )


def gemini_translate(text: str, source_lang: str, target_lang: str, config: dict, key: str, back_translate: bool = False) -> str:
    model = config.get("gemini_model") or GEMINI_MODELS[0]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{parse.quote(model)}:generateContent?key={parse.quote(key)}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": translation_prompt(text, source_lang, target_lang, config, back_translate)}],
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }
    data = read_http_json(url, payload=payload)
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini 没有返回候选结果")
    parts = candidates[0].get("content", {}).get("parts", [])
    translated = "".join(part.get("text", "") for part in parts).strip()
    if not translated:
        raise RuntimeError("Gemini 返回内容为空")
    return translated


def groq_translate(text: str, source_lang: str, target_lang: str, config: dict, key: str, back_translate: bool = False) -> str:
    payload = {
        "model": config.get("groq_model") or GROQ_MODELS[0],
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise translation engine. Return only the translated text.",
            },
            {
                "role": "user",
                "content": translation_prompt(text, source_lang, target_lang, config, back_translate),
            },
        ],
    }
    data = read_http_json(
        "https://api.groq.com/openai/v1/chat/completions",
        payload=payload,
        headers={"Authorization": f"Bearer {key}"},
    )
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Groq 没有返回候选结果")
    translated = choices[0].get("message", {}).get("content", "").strip()
    if not translated:
        raise RuntimeError("Groq 返回内容为空")
    return translated


def translate_with_ai(text: str, source_lang: str, target_lang: str, config: dict, back_translate: bool = False) -> tuple[str, str]:
    provider = config.get("ai_provider", "gemini")
    key_field = "gemini_keys" if provider == "gemini" else "groq_keys"
    keys = api_keys(config.get(key_field, ""))
    if not keys:
        raise RuntimeError("没有可用的 AI API KEY")

    errors = []
    for index, key in enumerate(keys, start=1):
        try:
            if provider == "gemini":
                return gemini_translate(text, source_lang, target_lang, config, key, back_translate), f"Gemini #{index}"
            return groq_translate(text, source_lang, target_lang, config, key, back_translate), f"Groq #{index}"
        except Exception as exc:
            errors.append(f"第 {index} 个密钥失败：{exc}")

    raise RuntimeError("; ".join(errors))


def translate_text(text: str, source_lang: str, target_lang: str, config: dict, back_translate: bool = False) -> tuple[str, str, str]:
    if back_translate:
        translated, provider = regular_translate(text, source_lang, target_lang, config.get("back_platform", "Google"), config)
        return translated, provider, ""

    translation_mode = config.get("translation_mode") or ("ai" if config.get("use_ai") else "google")
    if translation_mode == "ai":
        translated, provider = translate_with_ai(text, source_lang, target_lang, config, back_translate)
        return translated, provider, ""

    translated, provider = regular_translate(text, source_lang, target_lang, config.get("translation_platform", "Google"), config)
    return translated, provider, ""


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, background=BG)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas, style="App.TFrame")
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._update_width)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _update_width(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        if self.winfo_containing(event.x_root, event.y_root) in self.winfo_children_recursive():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def winfo_children_recursive(self):
        children = set()
        stack = [self]
        while stack:
            widget = stack.pop()
            children.add(widget)
            stack.extend(widget.winfo_children())
        return children


class LanguageBar(ttk.Frame):
    def __init__(self, parent, on_change):
        super().__init__(parent, style="Panel.TFrame")
        self.on_change = on_change
        self.language_codes = []
        self.active_code = ""
        self.buttons = []
        self.more_var = tk.StringVar()

        self.button_area = ttk.Frame(self, style="Panel.TFrame")
        self.button_area.grid(row=0, column=0, sticky="w")
        self.more_var.set("更多语言")
        self.more = ttk.Combobox(self, textvariable=self.more_var, values=LANGUAGE_LABELS, state="readonly", width=8)
        self.more.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.more.bind("<<ComboboxSelected>>", self._select_from_more)

    def set_languages(self, language_codes: list[str], active_code: str):
        self.language_codes = normalize_language_list(language_codes, language_codes or DEFAULT_CONFIG["my_languages"])
        self.active_code = active_code if active_code in LANGUAGE_NAMES else self.language_codes[0]
        if self.active_code not in self.language_codes:
            self.language_codes[-1] = self.active_code
        self.render()

    def render(self):
        for button in self.buttons:
            button.destroy()
        self.buttons.clear()

        for index, code in enumerate(self.language_codes):
            is_active = code == self.active_code
            button = tk.Button(
                self.button_area,
                text=LANGUAGE_NAMES.get(code, code),
                relief="flat",
                borderwidth=0,
                padx=7,
                pady=4,
                cursor="hand2",
                font="TranslatorLangBoldFont" if is_active else "TranslatorLangFont",
                fg=BLUE if is_active else TEXT,
                bg=PANEL,
                activeforeground=BLUE,
                activebackground=PANEL,
                command=lambda value=code: self._select(value),
            )
            button.grid(row=0, column=index, sticky="w")
            self.buttons.append(button)

    def _select(self, code: str):
        self.active_code = code
        self.render()
        self.on_change(code, self.language_codes)

    def _select_from_more(self, _event=None):
        code = LANGUAGE_CODES.get(self.more_var.get())
        if not code:
            return
        if code not in self.language_codes:
            self.language_codes[-1] = code
        self._select(code)
        self.more_var.set("更多语言")


class LanguagePicker(ttk.Frame):
    def __init__(self, parent, title: str, selected: list[str]):
        super().__init__(parent, style="Panel.TFrame")
        self.title = title
        self.selected = list(selected)
        self.buttons: dict[str, tk.Button] = {}
        self.columns = 0

        self.title_label = ttk.Label(self, text=title, style="Section.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.grid_columnconfigure(0, weight=1)
        self.options = ttk.Frame(self, style="Panel.TFrame")
        self.options.grid(row=1, column=0, sticky="ew")
        self.bind("<Configure>", self._on_options_resize)
        self.options.bind("<Configure>", self._on_options_resize)
        self._render_options()

    def _column_count(self) -> int:
        width = max(self.options.winfo_width(), self.winfo_width())
        if width >= 560:
            return 4
        if width >= 390:
            return 3
        if width >= 230:
            return 2
        return 1

    def _on_options_resize(self, _event=None):
        columns = self._column_count()
        if columns != self.columns:
            self._render_options(columns)
        else:
            self._update_button_geometry(columns)

    def _render_options(self, columns: int | None = None):
        columns = columns or self._column_count()
        if columns == self.columns and self.buttons:
            self._update_button_geometry(columns)
            return
        self.columns = columns
        for button in self.buttons.values():
            button.destroy()
        self.buttons.clear()
        for column in range(4):
            self.options.grid_columnconfigure(column, weight=0)
        for column in range(columns):
            self.options.grid_columnconfigure(column, weight=1, uniform="language")
        wrap = self._button_wraplength(columns)
        for index, (code, label) in enumerate(LANGUAGES):
            button = tk.Button(
                self.options,
                relief="solid",
                borderwidth=1,
                padx=4,
                pady=5,
                cursor="hand2",
                font="TranslatorBodyFont",
                justify="center",
                anchor="center",
                wraplength=wrap,
                command=lambda value=code: self.toggle(value),
            )
            button.grid(row=index // columns, column=index % columns, sticky="nsew", padx=3, pady=4)
            self.buttons[code] = button
        self.refresh()

    def _button_wraplength(self, columns: int) -> int:
        width = max(self.options.winfo_width(), self.winfo_width(), 180)
        return max(76, min(180, int((width - (columns - 1) * 6) / max(columns, 1)) - 18))

    def _update_button_geometry(self, columns: int | None = None):
        columns = columns or self.columns or self._column_count()
        wrap = self._button_wraplength(columns)
        self.title_label.configure(wraplength=max(120, self.winfo_width() - 8))
        for button in self.buttons.values():
            button.configure(wraplength=wrap)

    def toggle(self, code: str):
        if code in self.selected:
            if len(self.selected) == 1:
                messagebox.showinfo("保留一种语言", f"{self.title} 至少需要选择一种语言。")
                return
            self.selected.remove(code)
        else:
            if len(self.selected) >= 3:
                messagebox.showinfo("最多三种语言", f"{self.title} 最多只能选择三种语言。")
                return
            self.selected.append(code)
        self.refresh()

    def refresh(self):
        for code, button in self.buttons.items():
            active = code in self.selected
            button.configure(
                text=("✓ " if active else "  ") + LANGUAGE_NAMES[code],
                fg=BLUE if active else TEXT,
                bg="#eaf2ff" if active else PANEL,
                activebackground="#eaf2ff" if active else "#f2f5f9",
                highlightbackground=BLUE if active else BORDER,
            )

    def value(self) -> list[str]:
        return list(self.selected)

    def set_selected(self, selected: list[str]):
        self.selected = normalize_language_list(selected, self.selected or [LANGUAGES[0][0]])
        self.refresh()


class TranslatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.ui_language_var = tk.StringVar(
            value=UI_LANGUAGE_NAMES.get(self.config_data.get("ui_language", "zh-CN"), "中文（简体）")
        )
        self.result_queue: queue.Queue[tuple[str, TranslationResult | Exception]] = queue.Queue()
        self.direct_event_queue: queue.Queue[tuple[str, int]] = queue.Queue()
        self.translation_running = False
        self.speech_running = False
        self.speaking_running = False
        self.ui_scale = 1.0
        self.last_external_hwnd = None
        self.pending_translation_source = ""
        self.last_translation_source = ""
        self.ready_to_paste = False
        self.ready_to_send_external = False
        self.external_send_hwnd = None
        self.external_focus_hwnd = None
        self.external_caret_point = None
        self.external_restore_topmost = False
        self.direct_mode_enabled = False
        self.direct_phase = "idle"
        self.direct_enter_pending = False
        self.direct_toggle_pending = False
        self.direct_last_enter_at = 0.0
        self.direct_last_toggle_at = 0.0
        self.direct_translation_in_progress = False
        self.direct_external_hwnd = None
        self.keyboard_hook = None
        self.keyboard_proc = None
        self.own_root_hwnd = 0
        self.direct_hotkey_modifiers = ()
        self.direct_hotkey_vk = HOTKEY_KEY_TO_VK.get("Q", VK_D)
        self.direct_hotkey_label = DEFAULT_CONFIG["direct_hotkey"]
        self.floating_toggle = None
        self.floating_canvas = None
        self.floating_drag = None
        self.direct_hotkey_poll_pressed = False
        self._apply_direct_hotkey(self.config_data.get("direct_hotkey", DEFAULT_CONFIG["direct_hotkey"]))
        self.current_page = "translate"
        self.process_id = int(KERNEL32.GetCurrentProcessId()) if IS_WINDOWS and KERNEL32 is not None else 0

        self.title(self._ui("app_title"))
        self._apply_window_icon()
        self.minsize(330, 240)
        self.geometry(self.config_data.get("window_size", DEFAULT_CONFIG["window_size"]))
        self.configure(bg=BG)
        self._setup_fonts()
        self._setup_styles()
        self.attributes("-topmost", bool(self.config_data.get("always_on_top")))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.own_root_hwnd = self._own_hwnd()
        self._refresh_language_bars()
        self._refresh_back_panel()
        self._install_keyboard_hook()
        self.bind("<Configure>", self._on_window_resize)
        self.bind("<Unmap>", self._on_window_unmap)
        self.bind("<Map>", self._on_window_map)
        self.bind("<Return>", self._submit_from_keyboard)
        self.bind("<Control-Return>", self._submit_from_keyboard)
        self.after(250, self._track_foreground_window)
        self.after(100, self._poll_results)
        self.after(50, self._poll_direct_events)
        self.after(80, self._poll_direct_hotkey_state)

    def _apply_window_icon(self):
        icon_path = resource_path(APP_ICON)
        if not icon_path.exists():
            return
        try:
            self.iconbitmap(default=str(icon_path))
        except tk.TclError:
            pass

    def _floating_button_size(self) -> int:
        return normalize_floating_button_size(
            self.config_data.get("floating_button_size"), DEFAULT_CONFIG["floating_button_size"]
        )

    def _floating_active_color(self) -> str:
        preset = self.config_data.get("floating_active_color_preset", DEFAULT_CONFIG["floating_active_color_preset"])
        if preset in FLOAT_COLOR_PRESETS and preset != "custom":
            return FLOAT_COLOR_PRESETS[preset][0]
        return normalize_hex_color(
            self.config_data.get("floating_active_color"),
            DEFAULT_CONFIG["floating_active_color"],
        )

    def _color_preset_label(self, preset_key: str) -> str:
        _color, ui_key = FLOAT_COLOR_PRESETS.get(preset_key, FLOAT_COLOR_PRESETS["blue"])
        return self._ui(ui_key)

    def _color_preset_options(self) -> list[str]:
        return [self._color_preset_label(key) for key in FLOAT_COLOR_PRESETS]

    def _color_preset_key_from_label(self, label: str) -> str:
        for key in FLOAT_COLOR_PRESETS:
            if label == self._color_preset_label(key):
                return key
        return DEFAULT_CONFIG["floating_active_color_preset"]

    def _on_window_unmap(self, event):
        if event.widget is self:
            self.after(120, self._show_floating_toggle_if_minimized)

    def _on_window_map(self, event):
        if event.widget is self:
            self.after(120, self._hide_floating_toggle_if_restored)

    def _show_floating_toggle_if_minimized(self):
        try:
            if self.state() == "iconic":
                self._show_floating_toggle()
        except tk.TclError:
            pass

    def _hide_floating_toggle_if_restored(self):
        try:
            if self.state() != "iconic":
                self._hide_floating_toggle()
        except tk.TclError:
            pass

    def _show_floating_toggle(self):
        if self.floating_toggle is not None:
            try:
                if self.floating_toggle.winfo_exists():
                    self._position_floating_toggle()
                    self.floating_toggle.update_idletasks()
                    self._refresh_floating_toggle()
                    self.floating_toggle.deiconify()
                    self.floating_toggle.lift()
                    return
            except tk.TclError:
                self.floating_toggle = None
                self.floating_canvas = None

        top = tk.Toplevel(self)
        self.floating_toggle = top
        top.overrideredirect(True)
        top.configure(bg=FLOAT_TRANSPARENT_COLOR)
        try:
            top.attributes("-topmost", True)
            top.attributes("-transparentcolor", FLOAT_TRANSPARENT_COLOR)
        except tk.TclError:
            pass
        try:
            top.iconbitmap(default=str(resource_path(APP_ICON)))
        except tk.TclError:
            pass

        size = self._floating_button_size()
        canvas = tk.Canvas(
            top,
            width=size,
            height=size,
            bg=FLOAT_TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        canvas.pack()
        for widget in (canvas, top):
            widget.bind("<ButtonPress-1>", self._floating_button_press)
            widget.bind("<B1-Motion>", self._floating_button_drag)
            widget.bind("<ButtonRelease-1>", self._floating_button_release)
        self.floating_canvas = canvas
        self._position_floating_toggle()
        top.update_idletasks()
        self._refresh_floating_toggle()

    def _clamp_floating_position(self, x: int, y: int, size: int | None = None) -> tuple[int, int]:
        if self.floating_toggle is None:
            return x, y
        size = size if size is not None else self._floating_button_size()
        try:
            screen_width = self.floating_toggle.winfo_screenwidth()
            screen_height = self.floating_toggle.winfo_screenheight()
            x = max(0, min(int(x), max(0, screen_width - size)))
            y = max(0, min(int(y), max(0, screen_height - size)))
        except tk.TclError:
            pass
        return x, y

    def _configured_floating_position(self, size: int | None = None) -> tuple[int, int] | None:
        value = self.config_data.get("floating_position", "")
        if not isinstance(value, str):
            return None
        match = re.fullmatch(r"\s*(-?\d+)\s*,\s*(-?\d+)\s*", value)
        if not match:
            return None
        return self._clamp_floating_position(int(match.group(1)), int(match.group(2)), size)

    def _position_floating_toggle(self):
        if self.floating_toggle is None:
            return
        try:
            size = self._floating_button_size()
            configured = self._configured_floating_position(size)
            if configured is not None:
                x, y = configured
            else:
                screen_width = self.floating_toggle.winfo_screenwidth()
                screen_height = self.floating_toggle.winfo_screenheight()
                x = max(12, screen_width - size - 28)
                y = max(12, screen_height - size - 96)
            self.floating_toggle.geometry(f"{size}x{size}+{x}+{y}")
        except tk.TclError:
            pass

    def _refresh_floating_toggle(self):
        if self.floating_canvas is None:
            return
        try:
            canvas = self.floating_canvas
            size = self._floating_button_size()
            canvas.configure(width=size, height=size)
            if self.floating_toggle is not None:
                x, y = self._clamp_floating_position(
                    self.floating_toggle.winfo_x(),
                    self.floating_toggle.winfo_y(),
                    size,
                )
                self.floating_toggle.geometry(f"{size}x{size}+{x}+{y}")
            canvas.delete("all")
            fill = self._floating_active_color() if self.direct_mode_enabled else "#fbfdff"
            outline = BLUE if self.direct_mode_enabled else FLOAT_INACTIVE_BORDER
            stipple = "" if self.direct_mode_enabled else "gray12"
            pad = max(2, int(round(size * 0.06)))
            border_width = max(2, int(round(size * 0.04)))
            canvas.create_oval(
                pad,
                pad,
                size - pad,
                size - pad,
                fill=fill,
                outline=outline,
                width=border_width,
                stipple=stipple,
                tags=("hit",),
            )
            self._draw_floating_feather(canvas, size)
            if self.direct_mode_enabled:
                ring_pad = max(5, int(round(size * 0.11)))
                canvas.create_oval(
                    ring_pad,
                    ring_pad,
                    size - ring_pad,
                    size - ring_pad,
                    outline="#79cfff",
                    width=max(1, int(round(size * 0.03))),
                )
            canvas.update_idletasks()
        except tk.TclError:
            pass

    def _draw_floating_feather(self, canvas: tk.Canvas, size: int):
        def xy(x_ratio: float, y_ratio: float) -> tuple[int, int]:
            return int(round(size * x_ratio)), int(round(size * y_ratio))

        blade_outline = [
            *xy(0.66, 0.14),
            *xy(0.58, 0.20),
            *xy(0.51, 0.33),
            *xy(0.44, 0.50),
            *xy(0.36, 0.70),
            *xy(0.28, 0.86),
            *xy(0.39, 0.75),
            *xy(0.50, 0.58),
            *xy(0.59, 0.39),
            *xy(0.70, 0.20),
        ]
        blade_inner = [
            *xy(0.64, 0.17),
            *xy(0.57, 0.24),
            *xy(0.50, 0.39),
            *xy(0.43, 0.57),
            *xy(0.34, 0.78),
            *xy(0.44, 0.67),
            *xy(0.55, 0.49),
            *xy(0.65, 0.29),
        ]
        vein_start = xy(0.32, 0.84)
        vein_end = xy(0.65, 0.18)
        light_start = xy(0.39, 0.74)
        light_end = xy(0.60, 0.27)
        shadow_start = xy(0.32, 0.90)
        shadow_end = xy(0.51, 0.86)

        canvas.create_line(
            shadow_start,
            shadow_end,
            fill="#c9c9c9",
            width=max(1, int(round(size * 0.05))),
            capstyle="round",
        )
        canvas.create_polygon(
            blade_outline,
            fill="#0f5f9e",
            outline="#0a3e6c",
            width=max(1, int(round(size * 0.025))),
            smooth=True,
        )
        canvas.create_polygon(
            blade_inner,
            fill="#1f8bd6",
            outline="",
            smooth=True,
        )
        canvas.create_line(
            vein_start,
            vein_end,
            fill="#063f72",
            width=max(1, int(round(size * 0.045))),
            capstyle="round",
        )
        canvas.create_line(
            light_start,
            light_end,
            fill="#d8f4ff",
            width=max(1, int(round(size * 0.025))),
            capstyle="round",
        )

    def _hide_floating_toggle(self):
        if self.floating_toggle is None:
            return
        try:
            if self.floating_toggle.winfo_exists():
                self.floating_toggle.withdraw()
        except tk.TclError:
            self.floating_toggle = None
            self.floating_canvas = None

    def _floating_button_press(self, event):
        if self.floating_toggle is None:
            return
        try:
            self.floating_toggle.lift()
            self.floating_drag = {
                "start_x": int(event.x_root),
                "start_y": int(event.y_root),
                "window_x": int(self.floating_toggle.winfo_x()),
                "window_y": int(self.floating_toggle.winfo_y()),
                "last_x": int(self.floating_toggle.winfo_x()),
                "last_y": int(self.floating_toggle.winfo_y()),
                "moved": False,
            }
        except tk.TclError:
            self.floating_drag = None

    def _floating_button_drag(self, event):
        if self.floating_toggle is None or not self.floating_drag:
            return
        try:
            dx = int(event.x_root) - int(self.floating_drag["start_x"])
            dy = int(event.y_root) - int(self.floating_drag["start_y"])
            if abs(dx) > 3 or abs(dy) > 3:
                self.floating_drag["moved"] = True
            x, y = self._clamp_floating_position(
                int(self.floating_drag["window_x"]) + dx,
                int(self.floating_drag["window_y"]) + dy,
            )
            size = self._floating_button_size()
            self.floating_toggle.geometry(f"{size}x{size}+{x}+{y}")
            self.floating_drag["last_x"] = x
            self.floating_drag["last_y"] = y
            self.config_data["floating_position"] = f"{x},{y}"
        except tk.TclError:
            pass

    def _floating_button_release(self, event):
        drag = self.floating_drag
        self.floating_drag = None
        if not drag:
            return
        if not drag.get("moved"):
            self.toggle_direct_mode()
            self._refresh_floating_toggle()
            return
        if self.floating_toggle is not None:
            try:
                x, y = self._clamp_floating_position(
                    int(drag.get("last_x", self.floating_toggle.winfo_x())),
                    int(drag.get("last_y", self.floating_toggle.winfo_y())),
                )
                self.config_data["floating_position"] = f"{x},{y}"
            except tk.TclError:
                pass

    def _ui(self, key: str) -> str:
        language = self.config_data.get("ui_language", "zh-CN")
        return UI_TEXT.get(language, UI_TEXT["zh-CN"]).get(key, UI_TEXT["zh-CN"].get(key, key))

    def _setup_fonts(self):
        self.font_specs = {
            "header": ("TranslatorHeaderFont", 18, "bold"),
            "section": ("TranslatorSectionFont", 13, "bold"),
            "body": ("TranslatorBodyFont", 10, "normal"),
            "body_bold": ("TranslatorBodyBoldFont", 10, "bold"),
            "muted": ("TranslatorMutedFont", 9, "normal"),
            "status": ("TranslatorStatusFont", 9, "normal"),
            "lang": ("TranslatorLangFont", 11, "normal"),
            "lang_bold": ("TranslatorLangBoldFont", 11, "bold"),
            "mono": ("TranslatorMonoFont", 10, "normal"),
            "input": ("TranslatorInputFont", self.config_data.get("input_font_size", 13), "normal"),
            "output": ("TranslatorOutputFont", self.config_data.get("output_font_size", 13), "normal"),
            "back": ("TranslatorBackFont", self.config_data.get("back_font_size", 11), "normal"),
        }
        self.fonts = {}
        for key, (name, size, weight) in self.font_specs.items():
            family = "Consolas" if key == "mono" else "Microsoft YaHei UI"
            self.fonts[key] = tkfont.Font(self, name=name, family=family, size=size, weight=weight)

    def _font_name(self, key: str) -> str:
        return self.font_specs[key][0]

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Header.TLabel", background=BG, foreground=TEXT, font=self._font_name("header"))
        style.configure("Section.TLabel", background=PANEL, foreground=TEXT, font=self._font_name("section"))
        style.configure("SectionBg.TLabel", background=BG, foreground=TEXT, font=self._font_name("section"))
        style.configure("Label.TLabel", background=PANEL, foreground=TEXT, font=self._font_name("body"))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=self._font_name("muted"))
        style.configure("MutedBg.TLabel", background=BG, foreground=MUTED, font=self._font_name("muted"))
        style.configure("Status.TLabel", background=BG, foreground=MUTED, font=self._font_name("status"))
        style.configure("Primary.TButton", font=self._font_name("body_bold"))
        style.configure("TButton", font=self._font_name("body"))
        style.configure("Small.TButton", font=self._font_name("muted"), padding=(4, 1))
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=self._font_name("body"))
        style.configure("TRadiobutton", background=PANEL, foreground=TEXT, font=self._font_name("body"))

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(self, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, text=self._ui("app_title"), style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.status_var = tk.StringVar(value=self._ui("ready"))
        ttk.Label(header, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")

        self.nav = ttk.Frame(self, style="App.TFrame")
        self.nav.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))
        self.nav.grid_columnconfigure(4, weight=1)
        self.nav_buttons = {}
        for column, (page_name, text) in enumerate(
            (
                ("translate", self._ui("translate_tab")),
                ("settings", self._ui("settings_tab")),
                ("text", self._ui("text_tab")),
            )
        ):
            button = tk.Button(
                self.nav,
                text=text,
                width=9,
                height=1,
                relief="solid",
                borderwidth=1,
                cursor="hand2",
                font=self._font_name("body_bold"),
                fg=TEXT,
                bg=PANEL,
                activebackground="#eaf2ff",
                command=lambda value=page_name: self.show_page(value),
            )
            button.grid(row=0, column=column, sticky="w", padx=(0, 4))
            self.nav_buttons[page_name] = button

        self.direct_button = tk.Button(
            self.nav,
            text=self._ui("direct_tab"),
            width=9,
            height=1,
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            font=self._font_name("body_bold"),
            fg=TEXT,
            bg=PANEL,
            activebackground="#eaf2ff",
            command=self.toggle_direct_mode,
        )
        self.direct_button.grid(row=0, column=3, sticky="w", padx=(0, 4))

        self.page_host = ttk.Frame(self, style="App.TFrame")
        self.page_host.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)

        self.translate_page = ttk.Frame(self.page_host, style="App.TFrame")
        self.settings_page = ttk.Frame(self.page_host, style="App.TFrame")
        self.text_page = ttk.Frame(self.page_host, style="App.TFrame")
        for page in (self.translate_page, self.settings_page, self.text_page):
            page.grid(row=0, column=0, sticky="nsew")

        self._build_translate_page()
        self._build_settings_page()
        self._build_text_page()
        self.show_page("translate")

    def show_page(self, page_name: str):
        pages = {
            "translate": self.translate_page,
            "settings": self.settings_page,
            "text": self.text_page,
        }
        self.current_page = page_name
        pages[page_name].tkraise()
        for name, button in self.nav_buttons.items():
            selected = name == page_name
            button.configure(bg="#eaf2ff" if selected else PANEL, fg=BLUE if selected else TEXT)
        self._refresh_direct_button()
        if page_name == "translate":
            self.after_idle(self._focus_input_text_end)

    def toggle_direct_mode(self):
        if IS_WINDOWS and USER32 is not None and self.keyboard_hook is None:
            self._install_keyboard_hook()
        if not IS_WINDOWS or USER32 is None or self.keyboard_hook is None:
            self.status_var.set(self._ui("direct_unavailable"))
            return
        try:
            minimized = self.state() == "iconic"
        except tk.TclError:
            minimized = False
        self.direct_mode_enabled = not self.direct_mode_enabled
        self.direct_phase = "idle"
        self.direct_translation_in_progress = False
        self.ready_to_paste = False
        self.ready_to_send_external = False
        self._refresh_direct_button()
        if self.direct_mode_enabled and not minimized:
            self.show_page("translate")
        self.status_var.set(
            self._ui("direct_enabled" if self.direct_mode_enabled else "direct_disabled").format(
                hotkey=self.direct_hotkey_label
            )
        )
        self._refresh_floating_toggle()
        if self.floating_toggle is not None:
            try:
                self.floating_toggle.lift()
            except tk.TclError:
                pass

    def _refresh_direct_button(self):
        if not hasattr(self, "direct_button"):
            self._refresh_floating_toggle()
            return
        self.direct_button.configure(
            bg="#eaf2ff" if self.direct_mode_enabled else PANEL,
            fg=BLUE if self.direct_mode_enabled else TEXT,
        )
        self._refresh_floating_toggle()

    def _apply_direct_hotkey(self, value: str):
        normalized = normalize_direct_hotkey(value, DEFAULT_CONFIG["direct_hotkey"])
        modifiers, vk_code, label = parse_direct_hotkey(normalized) or parse_direct_hotkey(DEFAULT_CONFIG["direct_hotkey"])
        self.direct_hotkey_modifiers = modifiers
        self.direct_hotkey_vk = vk_code
        self.direct_hotkey_label = label
        self.config_data["direct_hotkey"] = label
        if hasattr(self, "direct_hotkey_var"):
            self.direct_hotkey_var.set(label)

    def _build_translate_page(self):
        page = self.translate_page
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        self.translate_panes = tk.PanedWindow(
            page,
            orient=tk.VERTICAL,
            sashwidth=7,
            sashrelief="raised",
            bd=0,
            bg=BG,
            opaqueresize=True,
        )
        self.translate_panes.grid(row=0, column=0, sticky="nsew")

        self.source_panel = self._panel(self.translate_panes)
        self.source_panel.grid_rowconfigure(1, weight=1)
        self.source_panel.grid_columnconfigure(0, weight=1)
        top_source = ttk.Frame(self.source_panel, style="Panel.TFrame")
        top_source.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        top_source.grid_columnconfigure(0, weight=1)
        self.source_bar = LanguageBar(top_source, self._source_language_changed)
        self.source_bar.grid(row=0, column=0, sticky="w")
        self.input_text = tk.Text(
            self.source_panel,
            wrap="word",
            undo=True,
            relief="flat",
            font=self._font_name("input"),
            foreground=TEXT,
            background=PANEL,
            insertbackground=TEXT,
            padx=8,
            pady=6,
        )
        self.input_text.grid(row=1, column=0, sticky="nsew")
        self.input_text.bind("<Return>", self._submit_from_keyboard)
        self.input_text.bind("<Control-Return>", self._submit_from_keyboard)
        self.input_text.bind("<Shift-Return>", self._insert_newline)
        source_audio = ttk.Frame(self.source_panel, style="Panel.TFrame")
        source_audio.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))
        self.listen_button = ttk.Button(
            source_audio,
            text="🎙",
            width=3,
            style="Small.TButton",
            command=self.start_speech_input,
        )
        self.listen_button.grid(row=0, column=0, sticky="w")
        self.speak_input_button = ttk.Button(
            source_audio,
            text="🔊",
            width=3,
            style="Small.TButton",
            command=self.speak_input_text,
        )
        self.speak_input_button.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.translate_button = ttk.Button(
            source_audio,
            text=self._ui("translate"),
            width=6,
            style="Small.TButton",
            command=self._submit_from_keyboard,
        )
        self.translate_button.grid(row=0, column=2, sticky="w", padx=(6, 0))
        self.clear_input_button = ttk.Button(
            source_audio,
            text=self._ui("clear"),
            width=6,
            style="Small.TButton",
            command=self.clear_texts,
        )
        self.clear_input_button.grid(row=0, column=3, sticky="w", padx=(6, 0))
        self.swap_button = ttk.Button(
            source_audio,
            text=self._ui("swap_languages"),
            width=9,
            style="Small.TButton",
            command=self.swap_languages,
        )
        self.swap_button.grid(row=0, column=4, sticky="w", padx=(6, 0))
        self.translate_panes.add(self.source_panel, minsize=54)

        self.target_panel = self._panel(self.translate_panes)
        self.target_panel.grid_rowconfigure(1, weight=1)
        self.target_panel.grid_columnconfigure(0, weight=1)
        self.target_bar = LanguageBar(self.target_panel, self._target_language_changed)
        self.target_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        self.output_text = tk.Text(
            self.target_panel,
            wrap="word",
            relief="flat",
            font=self._font_name("output"),
            foreground=TEXT,
            background=PANEL,
            padx=8,
            pady=6,
            state="disabled",
        )
        self.output_text.grid(row=1, column=0, sticky="nsew")
        target_audio = ttk.Frame(self.target_panel, style="Panel.TFrame")
        target_audio.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))
        self.speak_output_button = ttk.Button(
            target_audio,
            text="🔊",
            width=3,
            style="Small.TButton",
            command=self.speak_output_text,
        )
        self.speak_output_button.grid(row=0, column=0, sticky="w")
        self.copy_output_button = ttk.Button(
            target_audio,
            text=self._ui("copy_output"),
            width=8,
            style="Small.TButton",
            command=self.copy_output,
        )
        self.copy_output_button.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.translate_panes.add(self.target_panel, minsize=54)

        self.back_panel = self._panel(self.translate_panes)
        self.back_panel.grid_rowconfigure(1, weight=1)
        self.back_panel.grid_columnconfigure(0, weight=1)
        self.back_title_var = tk.StringVar(value=self._ui("back_translation"))
        ttk.Label(self.back_panel, textvariable=self.back_title_var, style="Section.TLabel").grid(
            row=0, column=0, sticky="w", padx=8, pady=(6, 0)
        )
        self.back_text = tk.Text(
            self.back_panel,
            wrap="word",
            relief="flat",
            height=3,
            font=self._font_name("back"),
            foreground=TEXT,
            background=PANEL,
            padx=8,
            pady=4,
            state="disabled",
        )
        self.back_text.grid(row=1, column=0, sticky="nsew")
        self.translate_panes.add(self.back_panel, minsize=38)
        self.back_panel_visible = True
        self.after(200, self._set_initial_pane_sizes)

    def _build_settings_page(self):
        scroller = ScrollableFrame(self.settings_page)
        scroller.grid(row=0, column=0, sticky="nsew")
        self.settings_page.grid_rowconfigure(0, weight=1)
        self.settings_page.grid_columnconfigure(0, weight=1)
        content = scroller.content
        content.grid_columnconfigure(0, weight=1)

        top_panel = self._panel(content)
        top_panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_panel.grid_columnconfigure(1, weight=1)
        self.always_on_top_var = tk.BooleanVar(value=bool(self.config_data.get("always_on_top")))
        ttk.Checkbutton(
            top_panel,
            text=self._ui("always_on_top"),
            variable=self.always_on_top_var,
            command=lambda: self.attributes("-topmost", bool(self.always_on_top_var.get())),
        ).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 8)
        )

        engine_panel = self._panel(content)
        engine_panel.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        engine_panel.grid_columnconfigure(0, weight=1)
        ttk.Label(engine_panel, text=self._ui("translation_method"), style="Section.TLabel").grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 12)
        )

        selected_mode = self.config_data.get("translation_mode") or ("ai" if self.config_data.get("use_ai") else "google")
        self.translation_mode_var = tk.StringVar(value=selected_mode)
        self.use_ai_var = tk.BooleanVar(value=selected_mode == "ai")
        self.translation_platform_var = tk.StringVar(value=self.config_data.get("translation_platform", "Google"))
        self.back_platform_var = tk.StringVar(value=self.config_data.get("back_platform", "Google"))
        mode_frame = ttk.Frame(engine_panel, style="Panel.TFrame")
        mode_frame.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))
        ttk.Radiobutton(
            mode_frame,
            text=self._ui("ai_translate"),
            variable=self.translation_mode_var,
            value="ai",
            command=self._refresh_translation_method_visibility,
        ).grid(row=0, column=0, padx=(0, 22))
        ttk.Radiobutton(
            mode_frame,
            text=self._ui("google_translate"),
            variable=self.translation_mode_var,
            value="google",
            command=self._refresh_translation_method_visibility,
        ).grid(row=0, column=1)

        self.ai_options_panel = ttk.Frame(engine_panel, style="Panel.TFrame")
        self.ai_options_panel.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.ai_options_panel.grid_columnconfigure(1, weight=1)

        self.ai_provider_var = tk.StringVar(value=self.config_data.get("ai_provider", "gemini"))
        provider_frame = ttk.Frame(self.ai_options_panel, style="Panel.TFrame")
        provider_frame.grid(row=0, column=1, sticky="w", padx=12, pady=8)
        ttk.Label(self.ai_options_panel, text=self._ui("ai_platform"), style="Label.TLabel").grid(row=0, column=0, sticky="w", padx=0, pady=8)
        ttk.Radiobutton(
            provider_frame,
            text="Gemini",
            variable=self.ai_provider_var,
            value="gemini",
            command=self._refresh_translation_method_visibility,
        ).grid(row=0, column=0, padx=(0, 18))
        ttk.Radiobutton(
            provider_frame,
            text="Groq AI",
            variable=self.ai_provider_var,
            value="groq",
            command=self._refresh_translation_method_visibility,
        ).grid(row=0, column=1)

        self.country_var = tk.StringVar(value=self.config_data.get("country", ""))
        self.gender_var = tk.StringVar(value=self.config_data.get("gender", "不指定"))
        self._labeled_entry(self.ai_options_panel, 1, self._ui("country"), self.country_var, "输入国家名称，AI会用当地特色翻译")
        self._labeled_combo(self.ai_options_panel, 2, self._ui("gender"), self.gender_var, ["不指定", "男性", "女性", "中性"])

        self.gemini_panel = ttk.Frame(self.ai_options_panel, style="Panel.TFrame")
        self.gemini_panel.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.gemini_panel.grid_columnconfigure(1, weight=1)
        self.gemini_keys = self._labeled_text(self.gemini_panel, 0, self._ui("gemini_key"), self.config_data.get("gemini_keys", ""))
        ttk.Label(self.gemini_panel, text=self._ui("gemini_key_help"), style="Muted.TLabel").grid(
            row=1, column=1, sticky="w", padx=12, pady=(0, 8)
        )
        self.gemini_model_var = tk.StringVar(value=self.config_data.get("gemini_model", GEMINI_MODELS[0]))
        self._labeled_combo(self.gemini_panel, 2, self._ui("gemini_model"), self.gemini_model_var, GEMINI_MODELS)

        self.groq_panel = ttk.Frame(self.ai_options_panel, style="Panel.TFrame")
        self.groq_panel.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.groq_panel.grid_columnconfigure(1, weight=1)
        self.groq_keys = self._labeled_text(self.groq_panel, 0, self._ui("groq_key"), self.config_data.get("groq_keys", ""))
        ttk.Label(self.groq_panel, text=self._ui("groq_key_help"), style="Muted.TLabel").grid(
            row=1, column=1, sticky="w", padx=12, pady=(0, 8)
        )
        self.groq_model_var = tk.StringVar(value=self.config_data.get("groq_model", GROQ_MODELS[1]))
        self._labeled_combo(self.groq_panel, 2, self._ui("groq_model"), self.groq_model_var, GROQ_MODELS)

        self.language_panel = self._panel(content)
        self.language_panel.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.language_panel.grid_columnconfigure(0, weight=1)
        self.language_panel.grid_columnconfigure(1, weight=1)
        self.my_picker = LanguagePicker(self.language_panel, self._ui("my_languages"), self.config_data.get("my_languages", []))
        self.their_picker = LanguagePicker(self.language_panel, self._ui("their_languages"), self.config_data.get("their_languages", []))
        self.language_panel.bind("<Configure>", self._layout_language_pickers)
        self.after_idle(self._layout_language_pickers)

        back_panel = self._panel(content)
        back_panel.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        back_panel.grid_columnconfigure(1, weight=1)
        ttk.Label(back_panel, text=self._ui("back_setting"), style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=18, pady=(18, 12))
        self.back_translate_var = tk.BooleanVar(value=bool(self.config_data.get("back_translate")))
        ttk.Radiobutton(back_panel, text=self._ui("back_yes"), variable=self.back_translate_var, value=True).grid(
            row=1, column=0, sticky="w", padx=18, pady=6
        )
        ttk.Radiobutton(back_panel, text=self._ui("back_no"), variable=self.back_translate_var, value=False).grid(
            row=2, column=0, sticky="w", padx=18, pady=6
        )
        ttk.Label(back_panel, text=self._ui("back_platform_setting"), style="Label.TLabel").grid(
            row=3, column=0, sticky="w", padx=18, pady=(12, 6)
        )
        back_platform_frame = ttk.Frame(back_panel, style="Panel.TFrame")
        back_platform_frame.grid(row=4, column=0, sticky="w", padx=18, pady=(0, 18))
        ttk.Radiobutton(
            back_platform_frame,
            text=self._ui("google_translate"),
            variable=self.back_platform_var,
            value="Google",
        ).grid(row=0, column=0, padx=(0, 22))
        ttk.Radiobutton(
            back_platform_frame,
            text=self._ui("microsoft_translate"),
            variable=self.back_platform_var,
            value="Microsoft",
        ).grid(row=0, column=1)
        self.microsoft_key_var = tk.StringVar(value=self.config_data.get("microsoft_key", ""))
        self.microsoft_region_var = tk.StringVar(value=self.config_data.get("microsoft_region", ""))
        self._labeled_entry(back_panel, 5, self._ui("microsoft_key"), self.microsoft_key_var, "")
        self._labeled_entry(back_panel, 6, self._ui("microsoft_region"), self.microsoft_region_var, "例如 eastasia / westus / global")
        ttk.Label(back_panel, text=self._ui("microsoft_key_help"), style="Muted.TLabel").grid(
            row=7, column=1, sticky="w", padx=12, pady=(0, 18)
        )

        direct_panel = self._panel(content)
        direct_panel.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        direct_panel.grid_columnconfigure(1, weight=1)
        ttk.Label(direct_panel, text=self._ui("direct_settings"), style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 12)
        )
        self.direct_hotkey_var = tk.StringVar(value=self.config_data.get("direct_hotkey", DEFAULT_CONFIG["direct_hotkey"]))
        self._labeled_entry(direct_panel, 1, self._ui("direct_hotkey_setting"), self.direct_hotkey_var, DEFAULT_CONFIG["direct_hotkey"])
        ttk.Label(direct_panel, text=self._ui("direct_hotkey_help"), style="Muted.TLabel").grid(
            row=2, column=1, sticky="w", padx=12, pady=(0, 10)
        )
        self.floating_button_size_var = tk.IntVar(value=self.config_data.get("floating_button_size", DEFAULT_CONFIG["floating_button_size"]))
        self._floating_button_size_control(
            direct_panel,
            3,
            self._ui("floating_button_size"),
            self.floating_button_size_var,
        )
        ttk.Label(direct_panel, text=self._ui("floating_button_size_help"), style="Muted.TLabel").grid(
            row=4, column=1, sticky="w", padx=12, pady=(0, 10)
        )
        preset_key = self.config_data.get("floating_active_color_preset", DEFAULT_CONFIG["floating_active_color_preset"])
        self.floating_color_preset_var = tk.StringVar(value=self._color_preset_label(preset_key))
        self.floating_color_preset_combo = self._labeled_combo(
            direct_panel,
            5,
            self._ui("floating_button_color_preset"),
            self.floating_color_preset_var,
            self._color_preset_options(),
        )
        self.floating_color_preset_combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_floating_color_preview())
        self.floating_custom_color_var = tk.StringVar(value=self.config_data.get("floating_active_color", DEFAULT_CONFIG["floating_active_color"]))
        custom_entry = self._labeled_entry(
            direct_panel,
            6,
            self._ui("floating_button_custom_color"),
            self.floating_custom_color_var,
            DEFAULT_CONFIG["floating_active_color"],
        )
        custom_entry.bind("<KeyRelease>", lambda _event: self._apply_floating_color_preview(validate=False))
        ttk.Label(direct_panel, text=self._ui("floating_button_color_help"), style="Muted.TLabel").grid(
            row=7, column=1, sticky="w", padx=12, pady=(0, 18)
        )

        actions = ttk.Frame(content, style="App.TFrame")
        actions.grid(row=5, column=0, sticky="ew", pady=(0, 24))
        actions.grid_columnconfigure(0, weight=1)
        ttk.Button(actions, text=self._ui("save_settings"), style="Primary.TButton", command=self.save_settings).grid(row=0, column=1, padx=(8, 0))
        self._refresh_translation_method_visibility()

    def _layout_language_pickers(self, event=None):
        if not hasattr(self, "language_panel"):
            return
        width = event.width if event is not None else self.language_panel.winfo_width()
        stacked = width < 620
        mode = "stacked" if stacked else "side_by_side"
        if getattr(self, "language_layout_mode", None) == mode:
            self.my_picker._on_options_resize()
            self.their_picker._on_options_resize()
            return

        self.language_layout_mode = mode
        self.my_picker.grid_forget()
        self.their_picker.grid_forget()

        if stacked:
            self.language_panel.grid_columnconfigure(0, weight=1, uniform="")
            self.language_panel.grid_columnconfigure(1, weight=0, uniform="")
            self.language_panel.grid_rowconfigure(0, weight=0)
            self.language_panel.grid_rowconfigure(1, weight=0)
            self.my_picker.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
            self.their_picker.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 18))
        else:
            self.language_panel.grid_columnconfigure(0, weight=1, uniform="language_picker")
            self.language_panel.grid_columnconfigure(1, weight=1, uniform="language_picker")
            self.language_panel.grid_rowconfigure(0, weight=0)
            self.language_panel.grid_rowconfigure(1, weight=0)
            self.my_picker.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
            self.their_picker.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)

        self.after_idle(self.my_picker._on_options_resize)
        self.after_idle(self.their_picker._on_options_resize)

    def _build_text_page(self):
        self.text_page.grid_columnconfigure(0, weight=1)

        panel = self._panel(self.text_page)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        panel.grid_columnconfigure(1, weight=1)

        ttk.Label(panel, text=self._ui("text_size_title"), style="Section.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(18, 6)
        )
        ttk.Label(panel, text=self._ui("text_size_hint"), style="Muted.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=18, pady=(0, 12)
        )

        self.input_font_size_var = tk.IntVar(value=self.config_data.get("input_font_size", 13))
        self.output_font_size_var = tk.IntVar(value=self.config_data.get("output_font_size", 13))
        self.back_font_size_var = tk.IntVar(value=self.config_data.get("back_font_size", 11))
        self._font_size_control(panel, 2, self._ui("input_font_size"), self.input_font_size_var)
        self._font_size_control(panel, 3, self._ui("output_font_size"), self.output_font_size_var)
        self._font_size_control(panel, 4, self._ui("back_font_size"), self.back_font_size_var)

        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.grid(row=5, column=0, columnspan=3, sticky="ew", padx=18, pady=(10, 18))
        actions.grid_columnconfigure(0, weight=1)
        ttk.Button(actions, text=self._ui("save_settings"), style="Primary.TButton", command=self.save_settings).grid(row=0, column=1)

        language_panel = self._panel(self.text_page)
        language_panel.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        language_panel.grid_columnconfigure(1, weight=1)

        ttk.Label(language_panel, text=self._ui("interface_language_title"), style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 6)
        )
        ttk.Label(language_panel, text=self._ui("interface_language_hint"), style="Muted.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12)
        )
        self._labeled_combo(language_panel, 2, self._ui("ui_language"), self.ui_language_var, UI_LANGUAGE_LABELS)

        language_actions = ttk.Frame(language_panel, style="Panel.TFrame")
        language_actions.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(10, 18))
        language_actions.grid_columnconfigure(0, weight=1)
        ttk.Button(language_actions, text=self._ui("save_settings"), style="Primary.TButton", command=self.save_settings).grid(row=0, column=1)

    def _font_size_control(self, parent, row: int, label: str, variable: tk.IntVar):
        ttk.Label(parent, text=label, style="Label.TLabel").grid(row=row, column=0, sticky="w", padx=18, pady=8)
        scale = tk.Scale(
            parent,
            variable=variable,
            from_=8,
            to=32,
            orient="horizontal",
            showvalue=False,
            resolution=1,
            bg=PANEL,
            highlightthickness=0,
            command=lambda _value: self._apply_text_fonts(),
        )
        scale.grid(row=row, column=1, sticky="ew", padx=12, pady=8)
        spinbox = tk.Spinbox(
            parent,
            from_=8,
            to=32,
            width=5,
            textvariable=variable,
            command=self._apply_text_fonts,
            font=self._font_name("body"),
        )
        spinbox.grid(row=row, column=2, sticky="w", padx=(0, 18), pady=8)
        spinbox.bind("<KeyRelease>", lambda _event: self._apply_text_fonts())

    def _floating_button_size_control(self, parent, row: int, label: str, variable: tk.IntVar):
        ttk.Label(parent, text=label, style="Label.TLabel").grid(row=row, column=0, sticky="w", padx=18, pady=8)
        scale = tk.Scale(
            parent,
            variable=variable,
            from_=36,
            to=120,
            orient="horizontal",
            showvalue=False,
            resolution=1,
            bg=PANEL,
            highlightthickness=0,
            command=lambda _value: self._apply_floating_button_size(),
        )
        scale.grid(row=row, column=1, sticky="ew", padx=12, pady=8)
        spinbox = tk.Spinbox(
            parent,
            from_=36,
            to=120,
            width=5,
            textvariable=variable,
            command=self._apply_floating_button_size,
            font=self._font_name("body"),
        )
        spinbox.grid(row=row, column=2, sticky="w", padx=(0, 18), pady=8)
        spinbox.bind("<KeyRelease>", lambda _event: self._apply_floating_button_size())

    def _safe_floating_button_size(self) -> int:
        variable = getattr(self, "floating_button_size_var", None)
        value = variable.get() if variable is not None else self.config_data.get("floating_button_size")
        return normalize_floating_button_size(value, DEFAULT_CONFIG["floating_button_size"])

    def _apply_floating_button_size(self):
        size = self._safe_floating_button_size()
        self.config_data["floating_button_size"] = size
        if hasattr(self, "floating_button_size_var"):
            try:
                if int(self.floating_button_size_var.get()) != size:
                    self.floating_button_size_var.set(size)
            except (tk.TclError, ValueError):
                self.floating_button_size_var.set(size)
        if self.floating_toggle is not None:
            self._refresh_floating_toggle()

    def _selected_floating_color_preset(self) -> str:
        if not hasattr(self, "floating_color_preset_var"):
            return self.config_data.get("floating_active_color_preset", DEFAULT_CONFIG["floating_active_color_preset"])
        return self._color_preset_key_from_label(self.floating_color_preset_var.get())

    def _apply_floating_color_preview(self, validate: bool = False) -> bool:
        preset = self._selected_floating_color_preset()
        if preset == "custom":
            raw_color = self.floating_custom_color_var.get() if hasattr(self, "floating_custom_color_var") else ""
            if validate and not is_hex_color(raw_color):
                messagebox.showerror(self._ui("settings_error"), self._ui("floating_button_color_invalid"))
                return False
            color = normalize_hex_color(raw_color, self.config_data.get("floating_active_color", DEFAULT_CONFIG["floating_active_color"]))
        else:
            color = FLOAT_COLOR_PRESETS[preset][0]
            if hasattr(self, "floating_custom_color_var"):
                self.floating_custom_color_var.set(color)

        self.config_data["floating_active_color_preset"] = preset
        self.config_data["floating_active_color"] = color
        self._refresh_floating_toggle()
        return True

    def _safe_font_size(self, variable: tk.IntVar, fallback: int) -> int:
        try:
            return min(32, max(8, int(variable.get())))
        except (tk.TclError, ValueError):
            return fallback

    def _apply_text_fonts(self):
        input_size = self._safe_font_size(getattr(self, "input_font_size_var", tk.IntVar(value=13)), 13)
        output_size = self._safe_font_size(getattr(self, "output_font_size_var", tk.IntVar(value=13)), 13)
        back_size = self._safe_font_size(getattr(self, "back_font_size_var", tk.IntVar(value=11)), 11)
        self.config_data["input_font_size"] = input_size
        self.config_data["output_font_size"] = output_size
        self.config_data["back_font_size"] = back_size
        self._apply_font_scale(force=True)

    def _on_window_resize(self, event):
        if event.widget is not self:
            return
        scale = min(event.width / 700, event.height / 540)
        scale = max(0.58, min(1.35, scale))
        if abs(scale - self.ui_scale) < 0.04:
            return
        self.ui_scale = scale
        self._apply_font_scale()

    def _scaled_size(self, size: int) -> int:
        return max(8, int(round(size * self.ui_scale)))

    def _apply_font_scale(self, force: bool = False):
        for key, (_name, base_size, _weight) in self.font_specs.items():
            if key == "input":
                base_size = self.config_data.get("input_font_size", 13)
            elif key == "output":
                base_size = self.config_data.get("output_font_size", 13)
            elif key == "back":
                base_size = self.config_data.get("back_font_size", 11)
            if key in ("input", "output", "back"):
                self.fonts[key].configure(size=max(8, int(base_size)))
            else:
                self.fonts[key].configure(size=self._scaled_size(int(base_size)))

        if hasattr(self, "translate_panes") and hasattr(self, "back_panel"):
            try:
                self.translate_panes.paneconfigure(self.source_panel, minsize=max(48, int(round(64 * self.ui_scale))))
                self.translate_panes.paneconfigure(self.target_panel, minsize=max(48, int(round(64 * self.ui_scale))))
                self.translate_panes.paneconfigure(self.back_panel, minsize=max(34, int(round(44 * self.ui_scale))))
            except tk.TclError:
                pass

    def _set_initial_pane_sizes(self):
        if not hasattr(self, "translate_panes") or not self.back_panel_visible:
            return
        height = self.translate_panes.winfo_height()
        if height < 150:
            self.after(150, self._set_initial_pane_sizes)
            return
        try:
            back_height = max(36, min(82, int(height * 0.16)))
            main_height = max(52, (height - back_height) // 2)
            self.translate_panes.sash_place(0, 0, main_height)
            self.translate_panes.sash_place(1, 0, main_height * 2)
        except tk.TclError:
            pass

    def _install_keyboard_hook(self):
        if not IS_WINDOWS or USER32 is None or LOW_LEVEL_KEYBOARD_PROC is None:
            return
        try:
            self.keyboard_proc = LOW_LEVEL_KEYBOARD_PROC(self._keyboard_hook_proc)
            module_handle = KERNEL32.GetModuleHandleW(None)
            self.keyboard_hook = USER32.SetWindowsHookExW(WH_KEYBOARD_LL, self.keyboard_proc, module_handle, 0)
            if not self.keyboard_hook:
                self.keyboard_proc = None
        except Exception:
            self.keyboard_hook = None
            self.keyboard_proc = None

    def _uninstall_keyboard_hook(self):
        if not IS_WINDOWS or USER32 is None or not self.keyboard_hook:
            return
        try:
            USER32.UnhookWindowsHookEx(self.keyboard_hook)
        except Exception:
            pass
        self.keyboard_hook = None
        self.keyboard_proc = None

    def _keyboard_hook_proc(self, n_code, w_param, l_param):
        try:
            if (
                n_code == HC_ACTION
                and int(w_param) in (WM_KEYDOWN, WM_SYSKEYDOWN)
            ):
                pointer_value = int(l_param) & ((1 << PTR_BITS) - 1)
                event_ptr = ctypes.cast(ctypes.c_void_p(pointer_value), ctypes.POINTER(KBDLLHOOKSTRUCT))
                info = event_ptr.contents
                if not (info.flags & LLKHF_INJECTED) and self._direct_hotkey_pressed(info.vkCode):
                    now = time.monotonic()
                    if now - self.direct_last_toggle_at < 0.6:
                        return 1
                    self.direct_last_toggle_at = now
                    if not self.direct_toggle_pending:
                        self.direct_toggle_pending = True
                        self.direct_event_queue.put(("toggle", 0))
                    return 1
                if info.vkCode == VK_RETURN and not (info.flags & LLKHF_INJECTED):
                    hwnd = int(USER32.GetForegroundWindow())
                    if self.direct_mode_enabled and self._is_valid_external_window_for_hook(hwnd):
                        now = time.monotonic()
                        if now - self.direct_last_enter_at < 0.18:
                            return 1
                        self.direct_last_enter_at = now
                        if not self.direct_enter_pending:
                            self.direct_enter_pending = True
                            self.direct_event_queue.put(("enter", hwnd))
                        return 1
        except Exception:
            pass
        return USER32.CallNextHookEx(self.keyboard_hook, n_code, w_param, l_param)

    def _direct_hotkey_pressed(self, vk_code: int) -> bool:
        if not IS_WINDOWS or USER32 is None:
            return False
        try:
            if int(vk_code) != int(self.direct_hotkey_vk):
                return False
            return self._direct_hotkey_state_pressed()
        except Exception:
            return False

    def _direct_hotkey_state_pressed(self) -> bool:
        if not IS_WINDOWS or USER32 is None:
            return False
        try:
            if not (USER32.GetAsyncKeyState(int(self.direct_hotkey_vk)) & 0x8000):
                return False
            return all(
                USER32.GetAsyncKeyState(HOTKEY_MODIFIER_VKS[modifier]) & 0x8000
                for modifier in self.direct_hotkey_modifiers
            )
        except Exception:
            return False

    def _poll_direct_hotkey_state(self):
        try:
            pressed = self._direct_hotkey_state_pressed()
            if pressed and not self.direct_hotkey_poll_pressed:
                now = time.monotonic()
                if now - self.direct_last_toggle_at >= 0.6 and not self.direct_toggle_pending:
                    self.direct_last_toggle_at = now
                    self.toggle_direct_mode()
            self.direct_hotkey_poll_pressed = pressed
        except Exception:
            self.direct_hotkey_poll_pressed = False
        self.after(80, self._poll_direct_hotkey_state)

    def _poll_direct_events(self):
        try:
            while True:
                event_type, hwnd = self.direct_event_queue.get_nowait()
                if event_type == "toggle":
                    self.direct_toggle_pending = False
                    self.toggle_direct_mode()
                elif event_type == "enter":
                    self._handle_direct_enter(hwnd)
        except queue.Empty:
            pass
        self.after(50, self._poll_direct_events)

    def _is_valid_external_window_for_hook(self, hwnd) -> bool:
        if not IS_WINDOWS or USER32 is None:
            return False
        try:
            hwnd = int(hwnd or 0)
        except (TypeError, ValueError):
            return False
        if hwnd == 0 or hwnd == int(self.own_root_hwnd or 0):
            return False
        if self._window_process_id(hwnd) == self.process_id:
            return False
        try:
            return bool(USER32.IsWindow(hwnd) and USER32.IsWindowVisible(hwnd))
        except Exception:
            return False

    def _handle_direct_enter(self, hwnd):
        try:
            if not self.direct_mode_enabled:
                return
            if not self._is_valid_external_window(hwnd):
                self.status_var.set(self._ui("direct_unavailable"))
                return
            if self.translation_running or self.direct_phase == "translating":
                self.status_var.set(self._ui("direct_waiting"))
                return
            if self.direct_phase == "translated":
                self._replace_external_input_with_translation(hwnd)
                return
            if self.direct_phase == "pasted":
                self._send_direct_external_message(hwnd)
                return
            self._start_direct_translation_from_external(hwnd)
        finally:
            self.direct_enter_pending = False

    def _start_direct_translation_from_external(self, hwnd):
        self.status_var.set(self._ui("direct_capturing"))
        self.update_idletasks()
        text = self._copy_external_input_text(hwnd)
        if not text:
            self.status_var.set(self._ui("direct_input_missing"))
            return

        self.direct_external_hwnd = hwnd
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", text)
        self._set_text(self.output_text, "")
        self._set_text(self.back_text, "")
        self.direct_phase = "translating"
        self.direct_translation_in_progress = True
        self.status_var.set(self._ui("direct_captured"))
        self.start_translation()
        if not self.translation_running:
            self.direct_phase = "idle"
            self.direct_translation_in_progress = False

    def _copy_external_input_text(self, hwnd) -> str:
        try:
            foreground = int(USER32.GetForegroundWindow()) if IS_WINDOWS and USER32 is not None else 0
        except Exception:
            foreground = 0
        if foreground != int(hwnd) and not self._focus_external_window(hwnd):
            return ""

        self._remember_external_input_focus(hwnd)
        had_clipboard_text = False
        old_clipboard_text = None
        try:
            old_clipboard_text = self.clipboard_get()
            had_clipboard_text = True
        except tk.TclError:
            pass

        try:
            self.clipboard_clear()
            self.update()
            time.sleep(0.14)
            self._send_ctrl_key(VK_A)
            time.sleep(0.1)
            self._send_ctrl_key(VK_C)
            for _ in range(10):
                time.sleep(0.05)
                self.update()
                try:
                    text = self.clipboard_get().strip()
                    if text:
                        return text
                except tk.TclError:
                    pass
            return ""
        finally:
            self.after(300, lambda: self._restore_clipboard_text(old_clipboard_text, had_clipboard_text))

    def _replace_external_input_with_translation(self, hwnd):
        output = self._get_text(self.output_text)
        if not output:
            self.status_var.set(self._ui("no_output"))
            return
        hwnd = hwnd if self._is_valid_external_window(hwnd) else self.direct_external_hwnd
        if not self._is_valid_external_window(hwnd) or not self._focus_external_window(hwnd):
            self.status_var.set(self._ui("paste_failed"))
            return

        had_clipboard_text = False
        old_clipboard_text = None
        try:
            old_clipboard_text = self.clipboard_get()
            had_clipboard_text = True
        except tk.TclError:
            pass

        self.clipboard_clear()
        self.clipboard_append(output)
        self.update()
        time.sleep(0.12)
        self._send_ctrl_key(VK_A)
        time.sleep(0.08)
        self._send_ctrl_v()
        self.direct_external_hwnd = hwnd
        self.direct_phase = "pasted"
        self.after(900, lambda: self._restore_clipboard_text(old_clipboard_text, had_clipboard_text))
        self.status_var.set(self._ui("direct_replaced"))

    def _send_direct_external_message(self, hwnd):
        hwnd = hwnd if self._is_valid_external_window(hwnd) else self.direct_external_hwnd
        if not self._is_valid_external_window(hwnd) or not self._focus_external_window(hwnd):
            self.status_var.set(self._ui("paste_failed"))
            return
        self.after(120, self._send_enter_key)
        self.after(360, self._clear_after_direct_send)

    def _clear_after_direct_send(self):
        self.input_text.delete("1.0", "end")
        self._set_text(self.output_text, "")
        self._set_text(self.back_text, "")
        self.direct_phase = "idle"
        self.direct_translation_in_progress = False
        self.direct_external_hwnd = None
        self.pending_translation_source = ""
        self.last_translation_source = ""
        self.ready_to_paste = False
        self.ready_to_send_external = False
        self.status_var.set(self._ui("direct_sent"))

    def _own_hwnd(self):
        try:
            hwnd = int(self.winfo_id())
            if IS_WINDOWS and USER32 is not None:
                root_hwnd = int(USER32.GetAncestor(hwnd, GA_ROOT))
                return root_hwnd or hwnd
            return hwnd
        except tk.TclError:
            return 0

    def _window_process_id(self, hwnd) -> int:
        if not IS_WINDOWS or USER32 is None:
            return 0
        try:
            process_id = ctypes.c_ulong()
            USER32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(process_id))
            return int(process_id.value)
        except Exception:
            return 0

    def _track_foreground_window(self):
        if IS_WINDOWS and USER32 is not None:
            try:
                hwnd = int(USER32.GetForegroundWindow())
                if self._is_valid_external_window(hwnd):
                    self.last_external_hwnd = hwnd
            except Exception:
                pass
        self.after(250, self._track_foreground_window)

    def _is_valid_external_window(self, hwnd) -> bool:
        if not IS_WINDOWS or USER32 is None:
            return False
        try:
            hwnd = int(hwnd or 0)
        except (TypeError, ValueError):
            return False
        if hwnd == 0 or hwnd == self._own_hwnd():
            return False
        if self._window_process_id(hwnd) == self.process_id:
            return False
        return bool(USER32.IsWindow(hwnd) and USER32.IsWindowVisible(hwnd))

    def _next_external_window(self):
        if not IS_WINDOWS or USER32 is None:
            return None
        hwnd = self._own_hwnd()
        for _ in range(80):
            hwnd = int(USER32.GetWindow(hwnd, GW_HWNDNEXT))
            if not hwnd:
                break
            if self._is_valid_external_window(hwnd):
                return hwnd
        return None

    def _paste_target_hwnd(self):
        if self._is_valid_external_window(self.last_external_hwnd):
            return self.last_external_hwnd
        return self._next_external_window()

    def _focus_external_window(self, hwnd) -> bool:
        if not self._is_valid_external_window(hwnd):
            return False
        try:
            if USER32.IsIconic(hwnd):
                USER32.ShowWindow(hwnd, SW_RESTORE)
            current_thread = int(KERNEL32.GetCurrentThreadId())
            target_thread = int(USER32.GetWindowThreadProcessId(hwnd, None))
            foreground = int(USER32.GetForegroundWindow())
            if self._window_process_id(foreground) == self.process_id and self._is_valid_external_window(self.last_external_hwnd):
                foreground = int(self.last_external_hwnd)
            foreground_thread = int(USER32.GetWindowThreadProcessId(foreground, None)) if foreground else 0

            attached_target = False
            attached_foreground = False
            if target_thread and target_thread != current_thread:
                attached_target = bool(USER32.AttachThreadInput(current_thread, target_thread, True))
            if foreground_thread and foreground_thread != current_thread and foreground_thread != target_thread:
                attached_foreground = bool(USER32.AttachThreadInput(current_thread, foreground_thread, True))
            try:
                USER32.BringWindowToTop(hwnd)
                return bool(USER32.SetForegroundWindow(hwnd))
            finally:
                if attached_foreground:
                    USER32.AttachThreadInput(current_thread, foreground_thread, False)
                if attached_target:
                    USER32.AttachThreadInput(current_thread, target_thread, False)
        except Exception:
            return False

    def _send_ctrl_v(self):
        if not IS_WINDOWS or USER32 is None:
            return
        USER32.keybd_event(VK_CONTROL, 0, 0, 0)
        USER32.keybd_event(VK_V, 0, 0, 0)
        USER32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        USER32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def _send_ctrl_key(self, vk_code: int):
        if not IS_WINDOWS or USER32 is None:
            return
        USER32.keybd_event(VK_CONTROL, 0, 0, 0)
        USER32.keybd_event(vk_code, 0, 0, 0)
        USER32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        USER32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def _send_enter_key(self):
        if not IS_WINDOWS or USER32 is None:
            return
        USER32.keybd_event(VK_RETURN, 0, 0, 0)
        USER32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)

    def _send_ctrl_v_and_remember_external_focus(self, hwnd):
        self._send_ctrl_v()
        self.after(180, lambda: self._remember_external_input_focus(hwnd))

    def _remember_external_input_focus(self, hwnd):
        if not IS_WINDOWS or USER32 is None or not self._is_valid_external_window(hwnd):
            return
        try:
            thread_id = int(USER32.GetWindowThreadProcessId(int(hwnd), None))
            info = GUITHREADINFO()
            info.cbSize = ctypes.sizeof(GUITHREADINFO)
            if not USER32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
                return

            focus_hwnd = int(info.hwndFocus or info.hwndCaret or 0)
            if focus_hwnd and USER32.IsWindow(focus_hwnd):
                self.external_focus_hwnd = focus_hwnd

            rect = info.rcCaret
            x = int((rect.left + rect.right) / 2) if rect.right or rect.left else int(rect.left)
            y = int((rect.top + rect.bottom) / 2) if rect.bottom or rect.top else int(rect.top)
            if x > 0 and y > 0:
                self.external_caret_point = (x, y)
        except Exception:
            pass

    def _restore_external_input_focus(self):
        if not IS_WINDOWS or USER32 is None:
            return
        focus_hwnd = int(self.external_focus_hwnd or 0)
        if focus_hwnd and USER32.IsWindow(focus_hwnd):
            try:
                current_thread = int(KERNEL32.GetCurrentThreadId())
                focus_thread = int(USER32.GetWindowThreadProcessId(focus_hwnd, None))
                attached = False
                if focus_thread and focus_thread != current_thread:
                    attached = bool(USER32.AttachThreadInput(current_thread, focus_thread, True))
                try:
                    USER32.SetFocus(focus_hwnd)
                finally:
                    if attached:
                        USER32.AttachThreadInput(current_thread, focus_thread, False)
            except Exception:
                pass

        if self.external_caret_point:
            try:
                x, y = self.external_caret_point
                USER32.SetCursorPos(int(x), int(y))
                USER32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                USER32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                pass

    def _focus_app_window(self):
        try:
            self.lift()
            self.focus_force()
            if IS_WINDOWS and USER32 is not None:
                USER32.SetForegroundWindow(self._own_hwnd())
        except tk.TclError:
            pass

    def _focus_input_text_end(self):
        if not hasattr(self, "input_text"):
            return
        self._focus_app_window()
        try:
            self.input_text.focus_set()
            self.input_text.mark_set("insert", "end-1c")
            self.input_text.see("insert")
        except tk.TclError:
            pass

    def _restore_clipboard_text(self, text: str | None, had_text: bool):
        if not had_text:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(text or "")
        except tk.TclError:
            pass

    def _panel(self, parent):
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=1)
        frame.configure(borderwidth=1, relief="solid")
        return frame

    def _labeled_entry(self, parent, row: int, label: str, variable: tk.StringVar, placeholder: str = ""):
        ttk.Label(parent, text=label, style="Label.TLabel").grid(row=row, column=0, sticky="w", padx=18, pady=8)
        entry = ttk.Entry(parent, textvariable=variable, font=self._font_name("body"))
        entry.grid(row=row, column=1, sticky="ew", padx=12, pady=8)
        if placeholder and not variable.get():
            entry.insert(0, "")
            entry.configure(foreground=TEXT)
        return entry

    def _labeled_combo(self, parent, row: int, label: str, variable: tk.StringVar, values: list[str]):
        ttk.Label(parent, text=label, style="Label.TLabel").grid(row=row, column=0, sticky="w", padx=18, pady=8)
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", font=self._font_name("body"), width=30)
        combo.grid(row=row, column=1, sticky="w", padx=12, pady=8)
        if variable.get() not in values:
            variable.set(values[0])
        return combo

    def _labeled_text(self, parent, row: int, label: str, value: str):
        ttk.Label(parent, text=label, style="Label.TLabel").grid(row=row, column=0, sticky="nw", padx=18, pady=8)
        text = tk.Text(
            parent,
            height=4,
            wrap="none",
            font=self._font_name("mono"),
            foreground=TEXT,
            background=PANEL,
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=7,
        )
        text.insert("1.0", value)
        text.grid(row=row, column=1, sticky="ew", padx=12, pady=8)
        return text

    def _refresh_translation_method_visibility(self):
        if not hasattr(self, "ai_options_panel"):
            return

        use_ai = self.translation_mode_var.get() == "ai"
        self.use_ai_var.set(use_ai)
        if not use_ai:
            self.ai_options_panel.grid_remove()
            return

        self.ai_options_panel.grid()
        if self.ai_provider_var.get() == "gemini":
            self.gemini_panel.grid()
            self.groq_panel.grid_remove()
        else:
            self.gemini_panel.grid_remove()
            self.groq_panel.grid()

    def _submit_from_keyboard(self, _event=None):
        if getattr(self, "current_page", "translate") != "translate":
            return None

        current_input = self.input_text.get("1.0", "end").strip()
        output = self._get_text(self.output_text)
        if self.ready_to_send_external and output and current_input == self.last_translation_source:
            self.send_external_message_and_clear()
        elif self.ready_to_paste and output and current_input == self.last_translation_source:
            self.paste_output_to_external()
        else:
            focus_widget = self.focus_get()
            if focus_widget is not self.input_text and not current_input:
                self._focus_input_text_end()
                return "break"
            self.start_translation()
        return "break"

    def _insert_newline(self, _event=None):
        self.input_text.insert("insert", "\n")
        return "break"

    def _sync_settings_from_widgets(self, validate: bool = False) -> bool:
        if not hasattr(self, "my_picker"):
            return True

        my_languages = self.my_picker.value()
        their_languages = self.their_picker.value()
        if validate and (not my_languages or not their_languages):
            messagebox.showerror("设置错误", "我的语言和对方语言都至少需要选择一种。")
            return False

        if not my_languages:
            my_languages = self.config_data.get("my_languages", DEFAULT_CONFIG["my_languages"])
        if not their_languages:
            their_languages = self.config_data.get("their_languages", DEFAULT_CONFIG["their_languages"])

        ui_language = UI_LANGUAGE_CODES.get(self.ui_language_var.get(), "zh-CN")
        translation_mode = self.translation_mode_var.get() if self.translation_mode_var.get() in ("ai", "google") else "google"
        ai_provider = self.ai_provider_var.get() if self.ai_provider_var.get() in ("gemini", "groq") else "gemini"
        translation_platform = self.translation_platform_var.get() if self.translation_platform_var.get() in ("Google", "Microsoft") else "Google"
        back_platform = self.back_platform_var.get() if self.back_platform_var.get() in ("Google", "Microsoft") else "Google"
        input_font_size = self._safe_font_size(self.input_font_size_var, self.config_data.get("input_font_size", 13))
        output_font_size = self._safe_font_size(self.output_font_size_var, self.config_data.get("output_font_size", 13))
        back_font_size = self._safe_font_size(self.back_font_size_var, self.config_data.get("back_font_size", 11))
        floating_button_size = self._safe_floating_button_size()
        floating_color_preset = self._selected_floating_color_preset()
        floating_color_raw = self.floating_custom_color_var.get() if hasattr(self, "floating_custom_color_var") else DEFAULT_CONFIG["floating_active_color"]
        if floating_color_preset == "custom":
            if not is_hex_color(floating_color_raw):
                if validate:
                    messagebox.showerror(self._ui("settings_error"), self._ui("floating_button_color_invalid"))
                    return False
                floating_color = self.config_data.get("floating_active_color", DEFAULT_CONFIG["floating_active_color"])
            else:
                floating_color = normalize_hex_color(floating_color_raw, DEFAULT_CONFIG["floating_active_color"])
        else:
            floating_color = FLOAT_COLOR_PRESETS[floating_color_preset][0]
        raw_direct_hotkey = self.direct_hotkey_var.get().strip() if hasattr(self, "direct_hotkey_var") else DEFAULT_CONFIG["direct_hotkey"]
        parsed_direct_hotkey = parse_direct_hotkey(raw_direct_hotkey)
        if not parsed_direct_hotkey:
            if validate:
                messagebox.showerror(self._ui("settings_error"), self._ui("direct_hotkey_invalid"))
                return False
            parsed_direct_hotkey = parse_direct_hotkey(DEFAULT_CONFIG["direct_hotkey"])
        direct_hotkey = parsed_direct_hotkey[2]

        self.config_data.update(
            {
                "always_on_top": self.always_on_top_var.get(),
                "ui_language": ui_language,
                "translation_mode": translation_mode,
                "use_ai": translation_mode == "ai",
                "ai_provider": ai_provider,
                "country": self.country_var.get().strip(),
                "gender": self.gender_var.get(),
                "gemini_keys": self.gemini_keys.get("1.0", "end").strip(),
                "groq_keys": self.groq_keys.get("1.0", "end").strip(),
                "gemini_model": self.gemini_model_var.get(),
                "groq_model": self.groq_model_var.get(),
                "translation_platform": translation_platform,
                "back_platform": back_platform,
                "microsoft_key": self.microsoft_key_var.get().strip(),
                "microsoft_region": self.microsoft_region_var.get().strip(),
                "my_languages": normalize_language_list(my_languages, DEFAULT_CONFIG["my_languages"]),
                "their_languages": normalize_language_list(their_languages, DEFAULT_CONFIG["their_languages"]),
                "back_translate": self.back_translate_var.get(),
                "input_font_size": input_font_size,
                "output_font_size": output_font_size,
                "back_font_size": back_font_size,
                "direct_hotkey": direct_hotkey,
                "floating_button_size": floating_button_size,
                "floating_active_color_preset": floating_color_preset,
                "floating_active_color": floating_color,
            }
        )
        self._apply_direct_hotkey(direct_hotkey)
        self._apply_floating_button_size()
        self._apply_floating_color_preview(validate=False)

        if self.config_data.get("source_lang") not in self.config_data["my_languages"]:
            self.config_data["source_lang"] = self.config_data["my_languages"][0]
        if self.config_data.get("target_lang") not in self.config_data["their_languages"]:
            self.config_data["target_lang"] = self.config_data["their_languages"][0]

        return True

    def _refresh_language_bars(self):
        self.source_bar.set_languages(self.config_data.get("my_languages", []), self.config_data.get("source_lang", "en"))
        self.target_bar.set_languages(self.config_data.get("their_languages", []), self.config_data.get("target_lang", "zh-CN"))

    def _refresh_back_panel(self):
        source_name = LANGUAGE_NAMES.get(self.config_data.get("source_lang", "en"), "")
        self.back_title_var.set(self._ui("back_to").format(source=source_name))
        if self.config_data.get("back_translate"):
            if not getattr(self, "back_panel_visible", False):
                self.translate_panes.add(self.back_panel, minsize=max(34, int(round(44 * self.ui_scale))))
                self.back_panel_visible = True
                self.after(50, self._set_initial_pane_sizes)
        else:
            if getattr(self, "back_panel_visible", False):
                self.translate_panes.forget(self.back_panel)
                self.back_panel_visible = False
                self.after(100, self._set_two_pane_sizes)

    def _set_two_pane_sizes(self):
        if not hasattr(self, "translate_panes") or getattr(self, "back_panel_visible", False):
            return
        height = self.translate_panes.winfo_height()
        if height < 160:
            self.after(150, self._set_two_pane_sizes)
            return
        try:
            self.translate_panes.sash_place(0, 0, height // 2)
        except tk.TclError:
            pass

    def _source_language_changed(self, code: str, language_codes: list[str]):
        self.config_data["source_lang"] = code
        self.config_data["my_languages"] = normalize_language_list(language_codes, self.config_data["my_languages"])
        if hasattr(self, "my_picker"):
            self.my_picker.set_selected(self.config_data["my_languages"])
        self._refresh_back_panel()

    def _target_language_changed(self, code: str, language_codes: list[str]):
        self.config_data["target_lang"] = code
        self.config_data["their_languages"] = normalize_language_list(language_codes, self.config_data["their_languages"])
        if hasattr(self, "their_picker"):
            self.their_picker.set_selected(self.config_data["their_languages"])

    def swap_languages(self):
        source = self.config_data.get("source_lang")
        target = self.config_data.get("target_lang")
        self.config_data["source_lang"], self.config_data["target_lang"] = target, source
        self._ensure_in_language_list("my_languages", target)
        self._ensure_in_language_list("their_languages", source)

        output = self._get_text(self.output_text)
        if output:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", output)
            self._set_text(self.output_text, "")
            self._set_text(self.back_text, "")
            self.ready_to_paste = False

        self._refresh_language_bars()
        self._refresh_back_panel()
        self.status_var.set(self._ui("swapped"))

    def _ensure_in_language_list(self, field: str, code: str):
        if code not in LANGUAGE_NAMES:
            return
        languages = normalize_language_list(self.config_data.get(field), DEFAULT_CONFIG[field])
        if code not in languages:
            languages[-1] = code
        self.config_data[field] = languages

    def start_translation(self):
        if self.translation_running:
            return
        self._sync_settings_from_widgets(validate=False)
        text = self.input_text.get("1.0", "end").strip()
        if not text:
            self.status_var.set(self._ui("input_required"))
            return

        source_lang = self.config_data.get("source_lang", "en")
        target_lang = self.config_data.get("target_lang", "zh-CN")
        if source_lang == target_lang:
            self.status_var.set(self._ui("same_language"))
            return

        config_snapshot = self.config_data.copy()
        self.translation_running = True
        self.ready_to_paste = False
        self.ready_to_send_external = False
        self.external_send_hwnd = None
        self.external_focus_hwnd = None
        self.external_caret_point = None
        self.external_restore_topmost = False
        self.pending_translation_source = text
        self.translate_button.configure(state="disabled")
        self.status_var.set(self._ui("translating"))
        self._set_text(self.output_text, "")
        self._set_text(self.back_text, "")

        thread = threading.Thread(
            target=self._translation_worker,
            args=(text, source_lang, target_lang, config_snapshot),
            daemon=True,
        )
        thread.start()

    def _translation_worker(self, text: str, source_lang: str, target_lang: str, config: dict):
        try:
            translated, provider, warning = translate_text(text, source_lang, target_lang, config)
            back_text = ""
            provider_label = provider
            if config.get("back_translate"):
                back_text, back_provider, back_warning = translate_text(translated, target_lang, source_lang, config, back_translate=True)
                provider_label = f"{provider_label} / 回译 {back_provider}"
                warning = warning or back_warning
            self.result_queue.put(("success", TranslationResult(translated, back_text, provider_label, warning)))
        except Exception as exc:
            self.result_queue.put(("error", exc))

    def _poll_results(self):
        try:
            status, payload = self.result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_results)
            return

        self.translation_running = False
        self.translate_button.configure(state="normal")

        if status == "success" and isinstance(payload, TranslationResult):
            self._set_text(self.output_text, payload.text)
            self._set_text(self.back_text, payload.back_text)
            self.last_translation_source = self.pending_translation_source
            if self.direct_translation_in_progress and self.direct_mode_enabled:
                self.ready_to_paste = False
                self.ready_to_send_external = False
                self.direct_phase = "translated" if payload.text else "idle"
                self.direct_translation_in_progress = False
                if payload.text:
                    self.status_var.set(self._ui("direct_ready"))
                    self._replace_external_input_with_translation(self.direct_external_hwnd)
                else:
                    self.status_var.set(self._ui("no_output"))
                self.external_send_hwnd = None
                self.external_focus_hwnd = None
                self.external_caret_point = None
                self.external_restore_topmost = False
                self.after(100, self._poll_results)
                return
            self.direct_translation_in_progress = False
            self.ready_to_paste = bool(payload.text)
            self.ready_to_send_external = False
            self.external_send_hwnd = None
            self.external_focus_hwnd = None
            self.external_caret_point = None
            self.external_restore_topmost = False
            if payload.warning:
                self.status_var.set(f"{self._ui('done').format(provider=payload.provider)}（{payload.warning[:80]}）")
            else:
                self.status_var.set(self._ui("done").format(provider=payload.provider))
        elif isinstance(payload, Exception):
            self.direct_translation_in_progress = False
            if self.direct_phase == "translating":
                self.direct_phase = "idle"
            self.ready_to_paste = False
            self.ready_to_send_external = False
            self.external_send_hwnd = None
            self.external_focus_hwnd = None
            self.external_caret_point = None
            self.external_restore_topmost = False
            self.status_var.set(self._ui("failed"))
            messagebox.showerror(self._ui("failed"), str(payload))

        self.after(100, self._poll_results)

    def save_settings(self):
        if not self._sync_settings_from_widgets(validate=True):
            return

        save_config(self.config_data)
        self.attributes("-topmost", bool(self.config_data.get("always_on_top")))
        self._refresh_language_bars()
        self._refresh_back_panel()
        self.status_var.set(self._ui("settings_saved"))
        messagebox.showinfo(self._ui("settings_saved"), self._ui("settings_saved_body"))

    def copy_output(self):
        output = self._get_text(self.output_text)
        if not output:
            self.status_var.set(self._ui("no_output"))
            return
        self.clipboard_clear()
        self.clipboard_append(output)
        self.status_var.set(self._ui("copied"))

    def start_speech_input(self):
        if self.speech_running:
            return
        self._sync_settings_from_widgets(validate=False)
        source_lang = self.config_data.get("source_lang", "en")
        self.speech_running = True
        self.listen_button.configure(state="disabled")
        self.status_var.set(self._ui("listening"))
        threading.Thread(target=self._speech_input_worker, args=(source_lang,), daemon=True).start()

    def _speech_input_worker(self, source_lang: str):
        try:
            text = recognize_speech(source_lang)
            self.after(0, self._speech_input_finished, text, None)
        except Exception as exc:
            self.after(0, self._speech_input_finished, "", exc)

    def _speech_input_finished(self, text: str, error: Exception | None):
        self.speech_running = False
        self.listen_button.configure(state="normal")
        if error is not None:
            self.status_var.set(self._ui("speech_failed"))
            messagebox.showerror(self._ui("speech_failed"), str(error))
            return

        current = self.input_text.get("1.0", "end-1c")
        if current and not current.endswith((" ", "\n")):
            self.input_text.insert("insert", " ")
        self.input_text.insert("insert", text)
        self.status_var.set(self._ui("speech_done"))

    def speak_input_text(self):
        self._start_speaking(self.input_text.get("1.0", "end").strip(), self.config_data.get("source_lang", "en"))

    def speak_output_text(self):
        self._start_speaking(self._get_text(self.output_text), self.config_data.get("target_lang", "zh-CN"))

    def _start_speaking(self, text: str, language_code: str):
        if self.speaking_running:
            return
        if not text:
            self.status_var.set(self._ui("speech_no_text"))
            return

        self.speaking_running = True
        self.speak_input_button.configure(state="disabled")
        self.speak_output_button.configure(state="disabled")
        self.status_var.set(self._ui("speaking"))
        threading.Thread(target=self._speak_worker, args=(text, language_code), daemon=True).start()

    def _speak_worker(self, text: str, language_code: str):
        try:
            speak_text(text, language_code)
            self.after(0, self._speak_finished, None)
        except Exception as exc:
            self.after(0, self._speak_finished, exc)

    def _speak_finished(self, error: Exception | None):
        self.speaking_running = False
        self.speak_input_button.configure(state="normal")
        self.speak_output_button.configure(state="normal")
        if error is not None:
            self.status_var.set(self._ui("speech_failed"))
            messagebox.showerror(self._ui("speech_failed"), str(error))
        else:
            self.status_var.set(self._ui("ready"))

    def paste_output_to_external(self):
        output = self._get_text(self.output_text)
        if not output:
            self.status_var.set(self._ui("no_output"))
            return

        if not IS_WINDOWS:
            self.copy_output()
            self.status_var.set(self._ui("paste_target_missing"))
            return

        hwnd = self._paste_target_hwnd()
        if not hwnd:
            self.copy_output()
            self.status_var.set(self._ui("paste_target_missing"))
            return

        had_clipboard_text = False
        old_clipboard_text = None
        try:
            old_clipboard_text = self.clipboard_get()
            had_clipboard_text = True
        except tk.TclError:
            pass

        self.clipboard_clear()
        self.clipboard_append(output)
        self.update()

        if not self._focus_external_window(hwnd):
            self.copy_output()
            self.status_var.set(self._ui("paste_failed"))
            return

        self.after(120, lambda: self._send_ctrl_v_and_remember_external_focus(hwnd))
        self.ready_to_paste = False
        self.ready_to_send_external = True
        self.external_send_hwnd = hwnd
        self.after(450, self._focus_input_text_end)
        self.after(900, lambda: self._restore_clipboard_text(old_clipboard_text, had_clipboard_text))
        self.status_var.set(self._ui("pasted_external"))

    def send_external_message_and_clear(self):
        if not IS_WINDOWS:
            self.status_var.set(self._ui("paste_target_missing"))
            return

        hwnd = self.external_send_hwnd if self._is_valid_external_window(self.external_send_hwnd) else self._paste_target_hwnd()
        if not hwnd:
            self.status_var.set(self._ui("paste_failed"))
            return

        try:
            self.external_restore_topmost = bool(self.attributes("-topmost"))
            if self.external_restore_topmost:
                self.attributes("-topmost", False)
        except tk.TclError:
            self.external_restore_topmost = False

        focused = self._focus_external_window(hwnd)
        if not focused and not self.external_caret_point:
            self._restore_topmost_after_external_send()
            self.status_var.set(self._ui("paste_failed"))
            return

        self.after(160, self._restore_external_input_focus)
        self.after(340, self._send_enter_key)
        self.after(560, self._clear_input_after_external_send)

    def _clear_input_after_external_send(self):
        self.input_text.delete("1.0", "end")
        self.ready_to_paste = False
        self.ready_to_send_external = False
        self.external_send_hwnd = None
        self.external_focus_hwnd = None
        self.external_caret_point = None
        self.pending_translation_source = ""
        self.last_translation_source = ""
        self.status_var.set(self._ui("sent_external"))
        self._restore_topmost_after_external_send()
        self._focus_input_text_end()

    def _restore_topmost_after_external_send(self):
        if not self.external_restore_topmost:
            return
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.external_restore_topmost = False

    def clear_texts(self):
        self.input_text.delete("1.0", "end")
        self._set_text(self.output_text, "")
        self._set_text(self.back_text, "")
        self.ready_to_paste = False
        self.ready_to_send_external = False
        self.external_send_hwnd = None
        self.external_focus_hwnd = None
        self.external_caret_point = None
        self.external_restore_topmost = False
        self.direct_phase = "idle"
        self.direct_translation_in_progress = False
        self.direct_external_hwnd = None
        self.pending_translation_source = ""
        self.last_translation_source = ""
        self.status_var.set(self._ui("cleared"))

    def _get_text(self, widget: tk.Text) -> str:
        state = str(widget.cget("state"))
        if state == "disabled":
            widget.configure(state="normal")
            value = widget.get("1.0", "end").strip()
            widget.configure(state="disabled")
            return value
        return widget.get("1.0", "end").strip()

    def _set_text(self, widget: tk.Text, value: str):
        state = str(widget.cget("state"))
        if state == "disabled":
            widget.configure(state="normal")
        widget.delete("1.0", "end")
        if value:
            widget.insert("1.0", value)
        if state == "disabled":
            widget.configure(state="disabled")

    def _on_close(self):
        try:
            self._sync_settings_from_widgets(validate=False)
            self.update_idletasks()
            self.config_data["window_size"] = normalize_window_size(
                f"{self.winfo_width()}x{self.winfo_height()}",
                self.config_data.get("window_size", DEFAULT_CONFIG["window_size"]),
            )
            save_config(self.config_data)
        finally:
            self._uninstall_keyboard_hook()
            if self.floating_toggle is not None:
                try:
                    self.floating_toggle.destroy()
                except tk.TclError:
                    pass
            self.destroy()


if __name__ == "__main__":
    app = TranslatorApp()
    app.mainloop()
