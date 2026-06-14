from app.forms.admin import BaseNoteForm
from app.forms.auth import LoginForm, RegistrationForm
from app.forms.collection import CollectionEntryForm, WishlistEntryForm
from app.forms.imports import ImportUploadForm

__all__ = [
    "BaseNoteForm",
    "CollectionEntryForm",
    "ImportUploadForm",
    "LoginForm",
    "RegistrationForm",
    "WishlistEntryForm",
]
