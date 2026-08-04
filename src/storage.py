import xml.etree.ElementTree as ET
from pathlib import Path

from aiogram.types import Chat, User

from model import Registration

OPTIONAL_FIELDS = (
    ("username", "Username"),
    ("first_name", "FirstName"),
    ("last_name", "LastName"),
    ("language_code", "LanguageCode"),
)


def read_registrations(registrations_path: Path) -> list[Registration]:
    if not registrations_path.exists():
        return []

    root = ET.parse(registrations_path).getroot()
    registrations: list[Registration] = []
    for element in root.findall("Registration"):
        name = element.findtext("Name")
        token = element.findtext("Token")
        chat_id = element.findtext("ChatId")
        if not name or not token or not chat_id:
            continue
        registrations.append(
            Registration(
                name=name,
                token=token,
                chat_id=int(chat_id),
                chat_type=element.findtext("ChatType", ""),
                title=element.findtext("Title"),
                username=element.findtext("Username"),
                first_name=element.findtext("FirstName"),
                last_name=element.findtext("LastName"),
                language_code=element.findtext("LanguageCode"),
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


def _set_child(element: ET.Element, tag: str, text: str) -> None:
    child = element.find(tag)
    if child is None:
        ET.SubElement(element, tag).text = text
    else:
        child.text = text


def _set_optional_child(element: ET.Element, tag: str, value: str | None) -> None:
    child = element.find(tag)
    if value:
        if child is None:
            ET.SubElement(element, tag).text = value
        else:
            child.text = value
    elif child is not None:
        element.remove(child)


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
    token: str,
    chat: Chat,
    user: User | None,
) -> Path:
    if registrations_path.exists():
        tree = ET.parse(registrations_path)
        root = tree.getroot()
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
        ET.SubElement(registration, "Token").text = token
        ET.SubElement(registration, "ChatId").text = str(chat.id)
        ET.SubElement(registration, "ChatType").text = chat.type
        _apply_optional_metadata(registration, chat, user)
    else:
        _set_child(existing, "Token", token)
        _set_child(existing, "ChatId", str(chat.id))
        _set_child(existing, "ChatType", chat.type)
        _apply_optional_metadata(existing, chat, user)

    registrations_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(registrations_path, encoding="utf-8", xml_declaration=True)
    return registrations_path
