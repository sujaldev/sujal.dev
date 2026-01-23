import fnmatch
from hashlib import md5
from pathlib import Path
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List


@dataclass
class VNode:
    name: str
    real_node: Path  # Each virtual node is backed by a real node in the actual file system.

    parent: "VNode | None" = field(default=None)
    children: Dict[str, "VNode"] = field(default_factory=dict)

    @property
    def path(self):
        if self.parent is None:
            return "."

        return f"{self.parent.path}/{self.name}"

    def is_dir(self):
        return self.real_node.is_dir()

    def is_file(self):
        return self.real_node.is_file()

    def rename(self, new_name: str):
        self.parent.children.pop(self.name)
        self.name = str(new_name)
        self.parent.children[self.name] = self

    @property
    def stem(self):
        """The final path component, minus its last suffix."""
        name = self.name
        i = name.rfind('.')
        if i != -1:
            stem = name[:i]
            # Stem must contain at least one non-dot character.
            if stem.lstrip('.'):
                return stem
        return name

    @property
    def suffix(self):
        """
        The final component's last suffix, if any.

        This includes the leading period. For example: '.txt'
        """
        name = self.name.lstrip('.')
        i = name.rfind('.')
        if i != -1:
            return name[i:]
        return ''

    @property
    def suffixes(self):
        """
        A list of the final component's suffixes, if any.

        These do not include the leading periods. For example: ['tar', 'gz']
        """
        return self.name.lstrip('.').split('.')[1:]

    def with_suffix(self, suffix):
        """
        Return a new path with the file suffix changed.  If the path
        has no suffix, add given suffix.  If the given suffix is an empty
        string, remove the suffix from the path.
        """

        return self.name[:-len(self.suffix)] + suffix

    def delete(self):
        # Removes the node from tree
        return self.parent.children.pop(self.name)

    def walk(self) -> Generator[VNode]:
        yield self

        for child in self.children.values():
            for grandchild in child.walk():
                yield grandchild

    def glob(self, pattern: str) -> List[VNode]:
        return [
            child for child in self.children.values() if fnmatch.fnmatch(child.name, pattern)
        ]

    def rglob(self, pattern: str) -> List[VNode]:
        return [
            node for node in self.walk() if fnmatch.fnmatch(node.name, pattern)
        ]

    def serialize(self):
        return {
            "name": self.name,
            "real_node": str(self.real_node.resolve()),
            "children": [
                child.serialize() for child in self.children.values()
            ]
        }

    @staticmethod
    def deserialize(serialized: Dict, _parent: VNode = None) -> VNode:
        node = VNode(serialized["name"], Path(serialized["real_node"]), _parent)
        node.children = {
            child["name"]: VNode.deserialize(child, node) for child in serialized["children"]
        }
        return node

    def __truediv__(self, other: str) -> VNode | None:
        # Locate an existing `VNode` in the virtual tree relative to this node.
        # Returns `None` if provided path does not exist.

        if not isinstance(other, str):
            raise Exception(f"Invalid {type(other)!r} for {self.__class__.__name__} path concatenation.")

        other = other.lstrip("/")
        node = self

        for part in other.split("/"):
            if not node:
                return None

            if not part or part == ".":
                continue

            if part == "..":
                node = node.parent
                continue

            if child := node.children.get(part):
                node = child
            else:
                return None

        return node

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.real_node}')"


class VTree:
    def __init__(self, src_dir: str | Path, ignored_dirs: Iterable[str] = None):
        if isinstance(src_dir, str):
            src_dir = Path(src_dir)
        self.src_dir = src_dir

        if ignored_dirs is None:
            ignored_dirs = DEFAULT_IGNORED_DIRS
        self.ignored_dirs = ignored_dirs

        self.root: VNode | None = None
        self.scan()

    def is_ignored_dir(self, path: Path):
        if not path.is_dir():
            return False

        name = path.name
        for pattern in self.ignored_dirs:
            if fnmatch.fnmatch(name, pattern):
                return True

        return False

    def _scan(self, path: Path, parent: VNode = None):
        if self.is_ignored_dir(path):
            return None

        node = VNode(path.name, path, parent)

        if not path.is_dir():
            return node

        for child in path.iterdir():
            child = self._scan(child, node)
            if child:
                node.children[child.name] = child

        return node

    def scan(self):
        self.root = self._scan(self.src_dir)
