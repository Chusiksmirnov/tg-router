import os
import xml.etree.ElementTree as ET
from pathlib import Path

from aiogram.types import Chat, User

from model import Registration


class StorageError(Exception):
    pass


OPTIONAL_FIELDS = (
    ("username", "Username"),
    ("first_name", "FirstName"),
    ("last_name", "LastName"),
    ("language_code", "LanguageCode"),
)


def read_registrations(registrations_path: Path) -> list[Registration]:
    if not registrations_path.exists():
        return []

    try:
        root = ET.parse(registrations_path).getroot()
    except ET.ParseError as error:
        raise StorageError(
            f"Cannot parse registrations file {registrations_path}: {error}"
        ) from error
    if root.tag != "Registrations":
        raise StorageError(
            f"Unexpected root element '{root.tag}' in {registrations_path}"
        )
    _ensure_unique_names(root, registrations_path)
    registrations: list[Registration] = []
    for element in root.findall("Registration"):
        name = element.findtext("Name")
        chat_id = element.findtext("ChatId")
        if not name:
            raise StorageError(
                f"Registration entry without a Name in {registrations_path}"
            )
        if not chat_id:
            raise StorageError(
                f"Registration '{name}' without a ChatId in {registrations_path}"
            )
        try:
            parsed_chat_id = int(chat_id)
        except ValueError as error:
            raise StorageError(
                f"Invalid ChatId '{chat_id}' for registration '{name}' "
                f"in {registrations_path}"
            ) from error
        registrations.append(
            Registration(
                name=name,
                chat_id=parsed_chat_id,
                chat_type=element.findtext("ChatType", ""),
                title=element.findtext("Title"),
                **{
                    attr: element.findtext(tag)
                    for attr, tag in OPTIONAL_FIELDS
                },
            )
        )
    return registrations


def get_registration(
    registrations_path: Path, name: str
) -> Registration | None:
    for registration in read_registrations(registrations_path):
        if registration.name == name:
            return registration
    return None


def _ensure_unique_names(root: ET.Element, registrations_path: Path) -> None:
    seen: set[str] = set()
    for element in root.findall("Registration"):
        name = element.findtext("Name")
        if name is None:
            continue
        if name in seen:
            raise StorageError(
                f"Duplicate registration name '{name}' in {registrations_path}"
            )
        seen.add(name)


def _set_child(element: ET.Element, tag: str, text: str) -> None:
    child = element.find(tag)
    if child is None:
        ET.SubElement(element, tag).text = text
    else:
        child.text = text


def _remove_child(element: ET.Element, tag: str) -> None:
    child = element.find(tag)
    if child is not None:
        element.remove(child)


def _set_optional_child(element: ET.Element, tag: str, value: str | None) -> None:
    child = element.find(tag)
    if value:
        if child is None:
            ET.SubElement(element, tag).text = value
        else:
            child.text = value
    else:
        _remove_child(element, tag)


def _apply_optional_metadata(
    element: ET.Element, chat: Chat, user: User | None
) -> None:
    _set_optional_child(element, "Title", chat.title)
    for attr, tag in OPTIONAL_FIELDS:
        value = getattr(user, attr, None) if user is not None else None
        _set_optional_child(element, tag, value)


def store_registration(
    registrations_path: Path,
    name: str,
    chat: Chat,
    user: User | None,
) -> Path:
    if registrations_path.exists():
        try:
            tree = ET.parse(registrations_path)
            root = tree.getroot()
        except ET.ParseError as error:
            raise StorageError(
                f"Cannot parse registrations file {registrations_path}: {error}"
            ) from error
        if root.tag != "Registrations":
            raise StorageError(
                f"Unexpected root element '{root.tag}' in {registrations_path}"
            )
        _ensure_unique_names(root, registrations_path)
    else:
        root = ET.Element("Registrations")
        tree = ET.ElementTree(root)

    existing = next(
        (
            item
            for item in root.findall("Registration")
            if item.findtext("Name") == name
        ),
        None,
    )
    if existing is None:
        registration = ET.SubElement(root, "Registration")
        ET.SubElement(registration, "Name").text = name
        ET.SubElement(registration, "ChatId").text = str(chat.id)
        ET.SubElement(registration, "ChatType").text = chat.type
        _apply_optional_metadata(registration, chat, user)
    else:
        _set_child(existing, "ChatId", str(chat.id))
        _set_child(existing, "ChatType", chat.type)
        _remove_child(existing, "Token")
        _apply_optional_metadata(existing, chat, user)

    registrations_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tmp_path = registrations_path.with_name(registrations_path.name + ".tmp")
    try:
        tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
        os.replace(tmp_path, registrations_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return registrations_path
