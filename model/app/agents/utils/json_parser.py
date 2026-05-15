import json
from typing import Any


class JsonParser:

    @staticmethod
    def parse(content: str, default=None) -> Any:
        if not content:
            return default

        content = content.strip()

        try:
            return json.loads(content)
        except Exception:
            pass

        markers = ["```json", "```"]

        for marker in markers:
            if marker in content:
                try:
                    data = content.split(marker)[1].split("```")[0]
                    return json.loads(data.strip())
                except Exception:
                    pass

        for sc, ec in [("{", "}"), ("[", "]")]:
            si = content.find(sc)
            ei = content.rfind(ec)

            if si != -1 and ei > si:
                try:
                    return json.loads(content[si:ei + 1])
                except Exception:
                    pass

        return default