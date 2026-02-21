import os
import re
import json

FRAMEWORK_SIGNATURES = {
    "FastAPI": [r"from\s+fastapi\s+import", r"import\s+fastapi"],
    "Flask": [r"from\s+flask\s+import", r"import\s+flask"],
    "Django": [r"from\s+django\s+", r"import\s+django"],
    "Express": [r"require\s*\(\s*['\"]express['\"]\s*\)", r"from\s+['\"]express['\"]"],
    "React": [r"from\s+['\"]react['\"]", r"import\s+.*\s+from\s+['\"]react['\"]", r"require\s*\(\s*['\"]react['\"]\s*\)", r"ReactDOM\.render", r"createRoot\s*\("],
    "Next.js": [r"next/config", r"next/head", r"next/link", r"next/router"],
    "NestJS": [r"@nestjs/", r"from\s+['\"]@nestjs/"],
    "Spring Boot": [r"org\.springframework\.boot", r"@SpringBootApplication"],
    "gin": [r"github\.com/gin-gonic/gin", r"gin\.New\("],
    "fiber": [r"github\.com/gofiber/fiber", r"fiber\.New\("],
    "Laravel": [r"Illuminate\\", r"use\s+Illuminate\\"],
    "ASP.NET": [r"Microsoft\.AspNetCore", r"using\s+Microsoft\.AspNetCore"],
}


def _detect_from_requirements(content: str) -> set:
    found = set()
    for line in content.splitlines():
        line = line.strip().lower().split("#")[0]
        if "fastapi" in line:
            found.add("FastAPI")
        if "flask" in line:
            found.add("Flask")
        if "django" in line:
            found.add("Django")
    return found


def _detect_from_package_json(content: str) -> set:
    found = set()
    try:
        data = json.loads(content)
        deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        dep_lower = {k.lower(): k for k in deps}
        if "express" in dep_lower:
            found.add("Express")
        if "react" in dep_lower:
            found.add("React")
        if "next" in dep_lower:
            found.add("Next.js")
        if "@nestjs/core" in dep_lower or "nestjs" in str(dep_lower):
            found.add("NestJS")
    except (json.JSONDecodeError, TypeError):
        pass
    return found


def _detect_from_pom(content: str) -> set:
    found = set()
    if "spring-boot" in content or "springframework.boot" in content:
        found.add("Spring Boot")
    return found


def _detect_from_go_mod(content: str) -> set:
    found = set()
    if "gin-gonic/gin" in content:
        found.add("gin")
    if "gofiber/fiber" in content:
        found.add("fiber")
    return found


def _detect_from_source(content: str) -> set:
    found = set()
    for fw, patterns in FRAMEWORK_SIGNATURES.items():
        for pat in patterns:
            if re.search(pat, content):
                found.add(fw)
                break
    return found


def detect_frameworks(repo_root: str, file_entries) -> list:
    all_frameworks = set()

    req_path = os.path.join(repo_root, "requirements.txt")
    if os.path.isfile(req_path):
        try:
            with open(req_path, "r", encoding="utf-8", errors="replace") as f:
                all_frameworks |= _detect_from_requirements(f.read())
        except Exception:
            pass

    pkg_path = os.path.join(repo_root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8", errors="replace") as f:
                all_frameworks |= _detect_from_package_json(f.read())
        except Exception:
            pass

    pom_path = os.path.join(repo_root, "pom.xml")
    if os.path.isfile(pom_path):
        try:
            with open(pom_path, "r", encoding="utf-8", errors="replace") as f:
                all_frameworks |= _detect_from_pom(f.read())
        except Exception:
            pass

    go_path = os.path.join(repo_root, "go.mod")
    if os.path.isfile(go_path):
        try:
            with open(go_path, "r", encoding="utf-8", errors="replace") as f:
                all_frameworks |= _detect_from_go_mod(f.read())
        except Exception:
            pass

    for rel_path, content in file_entries:
        if content:
            all_frameworks |= _detect_from_source(content)

    return sorted(all_frameworks)
