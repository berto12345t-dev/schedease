"""Required custom linked FIFO queue and unbalanced binary search tree."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterator, TypeVar

from schedule_models import Meeting, ScheduleState

T = TypeVar("T")


@dataclass
class BSTNode:
    key: int
    end_abs: int
    subject_code: str
    section: str
    left: BSTNode | None = None
    right: BSTNode | None = None
    blocked: bool = False
    title: str = ""
    day: str = ""
    start: str = ""
    end: str = ""
    reason: str = ""

    @classmethod
    def from_meeting(cls, meeting: Meeting) -> BSTNode:
        return cls(
            key=meeting.key,
            end_abs=meeting.end_abs,
            subject_code=meeting.subject_code,
            section=meeting.section,
            blocked=meeting.blocked,
            title=meeting.title,
            day=meeting.day,
            start=meeting.start,
            end=meeting.end,
            reason=meeting.reason,
        )


class BinarySearchTree:
    """BST ordered by day-index × 1440 + start minute."""

    def __init__(self, root: BSTNode | None = None):
        self.root = root
        self.size = 0 if root is None else sum(1 for _ in self.inorder())

    def insert(self, meeting: Meeting) -> None:
        node = BSTNode.from_meeting(meeting)
        if self.root is None:
            self.root = node
            self.size = 1
            return
        current = self.root
        while True:
            if node.key == current.key:
                raise ValueError("A meeting with this day and start time already exists in the BST.")
            if node.key < current.key:
                if current.left is None:
                    current.left = node
                    self.size += 1
                    return
                current = current.left
            else:
                if current.right is None:
                    current.right = node
                    self.size += 1
                    return
                current = current.right

    def predecessor_successor(self, key: int) -> tuple[BSTNode | None, BSTNode | None]:
        """Find the closest node at/before key and the closest node after key."""
        predecessor = None
        successor = None
        current = self.root
        while current is not None:
            if current.key <= key:
                predecessor = current
                current = current.right
            else:
                successor = current
                current = current.left
        return predecessor, successor

    def find_predecessor(self, key: int) -> BSTNode | None:
        return self.predecessor_successor(key)[0]

    def find_successor(self, key: int) -> BSTNode | None:
        return self.predecessor_successor(key)[1]

    def find_overlap(self, meeting: Meeting) -> BSTNode | None:
        """Use only the predecessor and successor to detect interval overlap."""
        predecessor, successor = self.predecessor_successor(meeting.key)
        if predecessor is not None and predecessor.end_abs > meeting.key:
            return predecessor
        if successor is not None and successor.key < meeting.end_abs:
            return successor
        return None

    def iter_inorder(self) -> Iterator[BSTNode]:
        """Yield nodes chronologically using an explicit O(h) traversal stack."""
        stack: list[BSTNode] = []
        current = self.root
        while current is not None or stack:
            while current is not None:
                stack.append(current)
                current = current.left
            current = stack.pop()
            yield current
            current = current.right

    def inorder(self) -> list[BSTNode]:
        """Return nodes in chronological order."""
        return list(self.iter_inorder())

    def deep_copy(self) -> BinarySearchTree:
        def clone(node: BSTNode | None) -> BSTNode | None:
            if node is None:
                return None
            return BSTNode(
                key=node.key,
                end_abs=node.end_abs,
                subject_code=node.subject_code,
                section=node.section,
                left=clone(node.left),
                right=clone(node.right),
                blocked=node.blocked,
                title=node.title,
                day=node.day,
                start=node.start,
                end=node.end,
                reason=node.reason,
            )

        copied = BinarySearchTree()
        copied.root = clone(self.root)
        copied.size = self.size
        return copied


@dataclass
class QueueNode(Generic[T]):
    state: T
    next: QueueNode[T] | None = None


class LinkedQueue(Generic[T]):
    """Singly linked FIFO queue with O(1) enqueue and dequeue."""

    def __init__(self):
        self.front: QueueNode[T] | None = None
        self.rear: QueueNode[T] | None = None
        self._size = 0

    def enqueue(self, state: T) -> None:
        node = QueueNode(state)
        if self.rear is None:
            self.front = self.rear = node
        else:
            self.rear.next = node
            self.rear = node
        self._size += 1

    def dequeue(self) -> T:
        if self.front is None:
            raise IndexError("dequeue from an empty queue")
        node = self.front
        self.front = node.next
        if self.front is None:
            self.rear = None
        self._size -= 1
        return node.state

    def peek(self) -> T:
        if self.front is None:
            raise IndexError("peek from an empty queue")
        return self.front.state

    def is_empty(self) -> bool:
        return self.front is None

    def display(self, describe: Callable[[T], str] | None = None) -> list[str]:
        """Return queue contents in FIFO order for diagnostics and traces."""
        items = []
        node = self.front
        while node is not None:
            if describe is not None:
                items.append(describe(node.state))
            elif isinstance(node.state, ScheduleState):
                items.append(
                    f"index={node.state.next_subject_index}, units={node.state.units}, "
                    f"selected={len(node.state.selected_sections)}"
                )
            else:
                items.append(str(node.state))
            node = node.next
        return items

    def __len__(self) -> int:
        return self._size
