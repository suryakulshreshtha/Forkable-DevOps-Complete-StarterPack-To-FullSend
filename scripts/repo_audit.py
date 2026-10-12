#!/usr/bin/env python3
"""Repository hygiene checks. CI runs this on every push.

1. Internal Markdown links point at files that exist.
2. No denied terms appear anywhere in tracked text files:
   * products and vendors excluded by this project's tool policy (see TOOLS.md), and
   * AI-attribution markers (AI co-author trailers, AI tool footers, AI tool names).
   The deny-list is stored as SHA-256 hashes so the repository itself never names
   the excluded products. Words are lower-cased and hashed one by one (and in pairs).
3. Optional (--external): every external link answers with a non-error status.

Usage:
  python scripts/repo_audit.py              # links + deny-list
  python scripts/repo_audit.py --external   # also check external links (needs internet)
"""

from __future__ import annotations

import hashlib
import itertools
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {
    *(".md", ".py", ".yml", ".yaml", ".json", ".toml", ".txt", ".tf", ".html", ".js", ".css"),
    *(".cfg", ".ini", ".sh", ".ps1", ".tpl", ""),
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".cache",
    ".terraform",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "test-results",
    "htmlcov",
}

DENIED: dict[str, frozenset[str]] = {
    "excluded-origin product or vendor": frozenset(
        {
            "047364b9be67f665eca384b8061d688b8642a8b47b3de35c22a012ed6fe69242",
            "0e4b2ba14f2fd7618e85092420c60bafabd0e868d2ad9944ff85192affb983b3",
            "10f716a4463bbd3ca8fb470bd307bb39077f35e334f4860b01fda826a0546ce6",
            "136db36b07faf276b5b9ed11f6d977d0176005435ccee50eba6f4fba998bd3f8",
            "143306bb5a0c3e59d0f5d89d76bc2e14f0a6896c16f108e1b64bc7047dc1f73d",
            "1535c450d6bc4a1432d3d3498e98c589fdb6bfb3428680fafb252432bbf5251f",
            "15ffebb4e29408ecad866dea59eb649e65a5406e0ba081da353bc6a5755f13a7",
            "185451f4cc9eada5354d0d968cdf56b3175ac7e15d699caa5656f2e6c151d765",
            "1aecc6b19a02163121aa8b8789782735f98eb6bffe07f5a4b8295415e0aa4666",
            "211074b6238601653abaed100a2a70e6c28dc2b9febd9564b50155e0878d4ffe",
            "2871823be240f8ecd1d72f24c99eaa2e58af18b4b8ba99a4fc2823ba5c43930a",
            "28be1fc3808080ef1890adbed541d104510630ca6a75123201e03cf6d2385503",
            "2a62945e88351cb2380621f1fef5a480a05ff933fe6c6b2fafac3ea06dee8291",
            "2a82e52f9257715a3a4c1ea76d7bec6e8429301c40f12a69b6b9c257e91b93dd",
            "2c348893efb2316e5f1753dd68e3da88bce6847ff8c7b6ea083fe1fd46d7061a",
            "2e233bb861908f231d9419588148209650218cf0a482e25aced196b661c68bc2",
            "2f457be173f2621d47d5872e0c702f4c98eb7fee56eda611489dc58748444e1a",
            "346050816901236bebcd846e945a4ff611927870d5d1bdb42c456e2b3414ab72",
            "3669ffb921cca6ee1edfe0f1e620fc2379771e9a8bd92659904540e984f3209e",
            "37a78441741fd1919fcdea5bb5850c860c1b2c4e8959d0cbcaa2247d5dd22993",
            "37da8069862f0bd7afeb7e71b28409f26609b8ee4f983ff859e63018d9aedb6c",
            "38ddd3dd36e813582edb23e696d8816790eff1eac213370249682e263e289979",
            "3fc38a59fe63618691f5af7af6121bbe158f22b99205ffd3036874e5bbfd627c",
            "41099c40dbfdcb1ca3a16fba2b6f3554e43f3764daf56bfb43017594ced8313b",
            "41b0d29cf7733e708c3a6584903c08d1152c6910ee3a8c19ad2c30f517495443",
            "42c31ef8ef857bb74635d7190d233ad9ac47d7fee595093a07dcb5dd5755b278",
            "42f4c1b243334ddbddbcc44b0271967461f3a59d2ef37b68006ff54011946092",
            "4340711050c96112780888943bee58999dd5ecd02db48ae2b4d5efef00c0c12a",
            "4402f7a7224b48fedb6fff262d36bd9345ad881cecd2918b11fc855f88dc12c2",
            "45cb5dd7401d56d213b3e3d7ee6f8f8145a5d90235b78698a543f59a7b8173fd",
            "45f02fc5240ccad27e363d3ca1f7ea91883d88e90b6a771193da142f0a7b9d28",
            "47b1b686727dee745b0d05da9c4e6264af5123705a20032e038d0cc8537cf262",
            "47c8e816dc45db9fb4e740e9e325211b547adc4140095d0073cab668f735b6a3",
            "4b916ac2be24abb93795a0c3b74ccdd19ffe283270b6959ad6adf3e2c753bd2b",
            "4c2e3eae0e819a491157d6e2d64bf8ba9ebf68e1cdd74ad6af613bd0a9e4f2b6",
            "4dbe391b8fcf977a0fe63bd5c113fcd351c22c09a8a1cbb47637a5e3d4fa907c",
            "4f27ea294089dc34a1b51f89f93cdfda45e339a0c54f02e13cf27a12415d1785",
            "4f5c33feddc2c8d7737ab930d049cf9f034252b73f7c0ef33c00c045ee28fc2b",
            "50fb974a65e0e362367037011e7ab525225b448028906e8e0f931ffa4921a90a",
            "5388bc10736a0eff09be2ab9c8369a9c1cd14ef7916dafe4e177da6903aefdec",
            "53ddd800a3ef24a55414bd607d995fe121836375b71ecbeb9d8d0eba710cce4f",
            "56018fe135c84cb3af995473a79669e46d0a02b12b8b3141aba2d2ad19d66f70",
            "569bf0af7a7562f31bbe4795656b6bdf307f7752163abc139157e3a3033b43ff",
            "5a5c07672a4efaf609e62d921a60bf7cc0e9722a8b9608520d694520c0c41407",
            "5ed0d740eb0d2ce6914f0f31415d8fc512dcaa579ff541bcc922459cde90e512",
            "657f07c63f72823fd8cc1738f70aa9ec03a0416c7df180fb32fc499173b54224",
            "6701119c9eb31cd349e8d7fa1ef1fb2f66e3cd8807112d7b293c2c7d46e9e4f3",
            "6749675d80a1faa70859312365b6eab644244d8e5d01cc94f44644c13d090ee7",
            "67ace226d55bf20bc69de199ba400ded2e914754707ddd32b4e495028109d901",
            "67f2d22514622d1be30c14ee9f3cb104503a159a33a656ca91a1953aa9616429",
            "694bdbb632339808e454046607c925d224689068cae77fd03d9443c5b3061301",
            "6f7ac1823da81d2e52d1a1549ee69c85bbf8bb56d06682849e7c09da2785ce3b",
            "71997c78b6d94581892b4481c1b75a59cddad48e19a8fed33adbe04e7ec2e56e",
            "73420e23f2089a37c2bb14d7331581606a917c971ad8bcef85515d48b83ed410",
            "742c86876526552edd894cfb4059233d7708f9976773c1503f11758e65f5592d",
            "78a2ba9fa731284aea9e3c7f63a32d55060e2d883102695d985645ef890337a9",
            "7a24358567cd5815813dcb1133e322a6e5ecdb1f21b4227b5ac46e53e8cca7d2",
            "7a65bc79c296ae06964d8339d03093032c788dc9f378aad806d48383a3ad5977",
            "7bdadccb53918eeaa16d8a31474cfefff5983711601e4ba4eeaa07896647038f",
            "88e2cce43eeadb36ce19668116709ef3f6f44b7b364d4d23fd545d2af826e6da",
            "8a105898989c6e17a605bdf926376050dd431701f4240ea084fc1c1d342cc848",
            "8abe43a7f9a7bd9403b75a17533bc38eea1e3d0f824bd392bd3ae0a864147238",
            "94fd83a0c6138c27ed82ca06f8b05128da8c8bad73be7388d9e98775f6d00312",
            "96274ca5ded72f3952a54c35ae74d23f129234da06d1de8b7aeed6246e57440c",
            "97e8959744b0cd308e3b9f47cc74f35668b4782e9fb682a37700c48d18a2e2c8",
            "983a94232604901238928219530a6fd451e66a5d2dd0ef12a32c8d633802a541",
            "995b35baf99499154a752376b7e906e4b93a2fde9c94d0828b31ad3670f5955d",
            "9c8ae69b84f21a2e46df9edf0063a697afec050188ff2884ddc8ab32b5e58c43",
            "9e3fdc838f0bb88c9e725f5d6e545a0058af9aec67c82c443e34642d122fc69e",
            "a282e0b70814f477de08fe0aa1218a7743e7beacd442f0f8068ceb66b8eff367",
            "a89151ba4b5ac0f22e96b71b963db927791d3808f5175f06ae4a60de5891bf0f",
            "a92d90407c9cd61ac9da5d392a07ec9789b248c6629a2cbf7a2c873b7f9e7812",
            "ac0db4f88ca5ea2c9ab086224aef53dffaf8a78b5b6b080fc0d86ac8f485038c",
            "af385f066fa6011aa6fb6606302c6bab5bea63da4f3099afa1802512d0b2cc1f",
            "b5d641b432cca81e57b5bb5b73c53e64c50d44dce93595a85d1d8885f48548e8",
            "b81c8201acfc7639be3bd3d7f875ba5ca76e422fa2163cec9dace50662b637a7",
            "ba480cfdba982f161584d3080b27336bedc4f34f790ca7685a75047fb9a99a25",
            "c159fd3a23342dc20d346131f0a02ef9e5650cbe6709f7e6cf58bca7cc6cf25b",
            "c1dee9c0155d6a0be2aaf58dee61ea136b2cc0e899b0c35590e5dbd96c311faa",
            "c3af43271ca5c989397c27dc110105646b22cd2f7c7a26b470d478b69ef2b495",
            "c42f8317fd35bd33d9e2321fdfee66b1fb41c4cc6ced5da50fe8e12650bc6f39",
            "c608c4787821de1b383d87ca8b2711d3d171b5a6c017c45a8523e9ae904d495e",
            "c71ad9859cd42209544283399a416be8837d418e19a642417b6a31617aed2a99",
            "cd3ebf2708df4d4c6cdb3d90e5e7456c6bc080c03e8cd4573a31671d15adff94",
            "ced422ed4a8498b96b7892665822008a76e6fb4d2b448e12e8741663cea53ece",
            "d7c911f6939a18832e05241a8d8764d7ff7871b75881a029fd92b785bd21dd78",
            "d977520b7963d84eaf4af4a8bc8fcab7b7824a00ee913503568e2a83af200463",
            "dc4cb570e960a328a01942800756bfd90879e4b719f1b9fd221f2349132eb503",
            "ddf54780ccfa414f2096f791e1f799c4aaeece85367c6cdc37291df12283c144",
            "de85c72a1f4d833ccba2a3566f416d110cccee017a76faf02e29c7da3761e007",
            "e1517be14d06cdb72af7bb52a289a0d5eab667e8b52ec4bac02914e1245f8a40",
            "e449ac7d5a882c92fef07a56c435eae23a966c9d8d28386d11afbd77d1a1e515",
            "e4be74b69f36e8090c3e287a9aff3363a0c43f2a3c18f21835834d48351c6118",
            "e4f9c522e1c89280e9561b825f4f24fe32b51ff82d61e5c2b1dfd0321c35a90b",
            "e9fc4f156e36f6aa73841dbabb5ab2eec71f482c058b005158fcbf4912b21ee6",
            "ec2ca6ae595c68d8b28a58aecdcc28509854dc4870f6995228d6d5daefbfdb2d",
            "f01ea329ad9fc5d007b0e0442ad991f93b0c4be9f0ee729cffd1194774a1eeaf",
            "f0caa84132f0c2f594dbafd63bb46bae98c73b38180f3e2611c8423897b7167e",
            "f551abbf895a80728506e95d4ed1e60b28e9577ac39935adf8461ba8d3ecd096",
            "f739ca683270038d84eca3bc1d90859ebb855cbd815af30ef2fa612835365fa6",
            "f931d572c1d4a548e812e2ff314742668e812af4cfe00052796551cbdfc9e1bd",
            "f95d5af831e91b9438159e4b89998da6c1e446bce2fb5b7f34f2f2fc7dcd098a",
            "fb49d6d5dd712290f262eafa7238e32e6e645612e6fc8680e1ee4150e057cbf3",
            "fb646a85ad74e7c57684e866f24ef08b4461ea1914856d5d194bb27b28b5cf15",
        }
    ),
    "AI-attribution marker": frozenset(
        {
            "2e8aae79d9566c6391cbf216d0b40760bde9bd51a6c5b0b970a248f679cd718f",
            "3ea125d0bff386e6754b3782b300016fc79a9cf8f8669c0a5c3db64467ddb681",
            "55383d1dc3467942036e90f3bf012f06e27e4ad28469fafa186a6966f29b1748",
            "5d72436256ada53828b51895a94bb8489e9f1ac4fe937a8024ef1594e7045ff6",
            "60965168ce762e949600281ba6d01fee136e5b6e8257b1f216f9025ed324474c",
            "7086a5e04b87f69a2af70092fc9f8205243f75d4bb1afe5f26b102f73b9eff09",
            "746d1113c358e1c93874b12761fba6298d99d01aec38a47f13df47b94d129b37",
            "7813670ff886c2f9397c151cf25b097663b3b1edda5c403ebf162982972b2c8e",
            "7d3194f79e645c42e4396dda38be04766810ec6a00d00aced3ffc2a0a1f1a9ef",
            "8316b399af66208937f9fe28d70a160fa0d26060ab53df53cb5ab55c10eb4cfe",
            "c70eca6b0f88f44d81a41311647e50fda1ac454ec04ffd442b0eb4743a993131",
            "c857d09db23e6822e3600bc06ad8d58f92ed62bc8efd81c753f77048662cb97d",
        }
    ),
}

# The license must stay word-for-word, so the deny-list does not scan it.
VERBATIM_FILES = {"LICENSE"}

WORD = re.compile(r"[a-z0-9][a-z0-9-]*")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
URL = re.compile(r"https?://[^\s)<>\"'`\]]+")


def tracked_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        wanted = path.suffix in TEXT_SUFFIXES and not SKIP_DIRS.intersection(rel.parts)
        if path.is_file() and wanted:
            files.append(path)
    return sorted(files)


def digest(term: str) -> str:
    return hashlib.sha256(term.encode()).hexdigest()


def line_findings(line: str) -> list[tuple[str, str]]:
    """Return (category, hash) for every denied term in one line of text."""
    words = WORD.findall(line.lower())
    # "name-v2" and "name3-coder" should still match "name": also check the parts
    # of hyphenated words and each token without trailing digits.
    parts = [p for w in words if "-" in w for p in w.split("-") if p]
    stems = [re.sub(r"\d+$", "", t) for t in (*words, *parts)]
    pairs = [f"{a} {b}" for a, b in itertools.pairwise(words)]
    candidates = dict.fromkeys(t for t in (*words, *parts, *stems, *pairs) if t)
    findings = []
    for term in candidates:
        hashed = digest(term)
        for category, hashes in DENIED.items():
            if hashed in hashes:
                findings.append((category, hashed))
    return findings


def denied_terms(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return problems
    for number, line in enumerate(lines, start=1):
        for category, hashed in line_findings(line):
            where = f"{path.relative_to(ROOT)}:{number}"
            problems.append(f"{where}: {category} (hash {hashed[:10]})")
    return problems


def broken_internal_links(path: Path) -> list[str]:
    problems = []
    text = path.read_text(encoding="utf-8")
    for target in MD_LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        file_part = target.split("#", 1)[0]
        if file_part and not (path.parent / file_part).exists():
            problems.append(f"{path.relative_to(ROOT)}: broken link -> {target}")
    return problems


def external_links(files: list[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in files:
        if path.suffix != ".md":
            continue
        for url in URL.findall(path.read_text(encoding="utf-8")):
            url = url.rstrip(".,;:")
            if "<" in url or "example.com" in url or "localhost" in url or "127.0.0.1" in url:
                continue
            found.setdefault(url, []).append(str(path.relative_to(ROOT)))
    return found


def check_external(urls: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    for url, where in sorted(urls.items()):
        request = urllib.request.Request(url, headers={"User-Agent": "repo-audit/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=20) as res:  # nosec B310  # documentation links
                status = res.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except (urllib.error.URLError, TimeoutError) as exc:
            warnings.append(f"{url} unreachable ({exc}) in {where[0]}")
            continue
        if status in (401, 403, 429):
            warnings.append(f"{url} answered {status} (sites often block scripts) in {where[0]}")
        elif status >= 400:
            errors.append(f"{url} answered {status} in {', '.join(where[:3])}")
    return errors, warnings


def main(argv: list[str]) -> int:
    files = tracked_files()
    problems: list[str] = []
    for path in files:
        if path.resolve() == Path(__file__).resolve():
            continue
        if path.name not in VERBATIM_FILES:
            problems += denied_terms(path)
        if path.suffix == ".md":
            problems += broken_internal_links(path)
    warnings: list[str] = []
    if "--external" in argv:
        errors, warnings = check_external(external_links(files))
        problems += errors
    for p in problems:
        print(f"✗ {p}")
    for w in warnings:
        print(f"! {w}")
    print(f"audited {len(files)} files: {len(problems)} problem(s), {len(warnings)} warning(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
