"""Conversation states for Telegram bot."""
from enum import Enum, auto


class ConversationStates(Enum):
    """Conversation states for bot interactions."""
    
    # Main menu navigation
    MAIN_MENU = auto()
    
    # User registration flow
    REGISTRATION_START = auto()
    REGISTRATION_NAME = auto()
    REGISTRATION_LANGUAGE = auto()
    REGISTRATION_TIMEZONE = auto()
    REGISTRATION_COMPLETE = auto()
    
    # Child management
    ADD_CHILD_NAME = auto()
    ADD_CHILD_AGE = auto()
    ADD_CHILD_BIRTH_DATE = auto()
    ADD_CHILD_GENDER = auto()
    ADD_CHILD_PERSONALITY = auto()
    ADD_CHILD_INTERESTS = auto()
    ADD_CHILD_SPECIAL_NEEDS = auto()
    ADD_CHILD_CONFIRM = auto()
    
    EDIT_CHILD_SELECT = auto()
    EDIT_CHILD_FIELD = auto()
    EDIT_CHILD_VALUE = auto()
    
    # Emotion translation flow
    EMOTION_SELECT_CHILD = auto()
    EMOTION_ENTER_MESSAGE = auto()
    EMOTION_ADD_CONTEXT = auto()
    EMOTION_PROCESSING = auto()
    EMOTION_SHOW_RESULTS = auto()
    
    # Settings management
    SETTINGS_MENU = auto()
    SETTINGS_LANGUAGE = auto()
    SETTINGS_TIMEZONE = auto()
    SETTINGS_NOTIFICATIONS = auto()
    
    # Family member management
    FAMILY_ADD_MEMBER = auto()
    FAMILY_MEMBER_NAME = auto()
    FAMILY_MEMBER_ROLE = auto()
    FAMILY_MEMBER_PERMISSIONS = auto()
    
    # Check-in responses
    CHECKIN_RESPONSE = auto()
    CHECKIN_FOLLOW_UP = auto()
    
    # Reports and analytics
    VIEW_REPORTS = auto()
    REPORT_TIMEFRAME = auto()
    REPORT_CHILD_SELECT = auto()
    
    # Help and support
    HELP_MENU = auto()
    CONTACT_SUPPORT = auto()
    
    # Admin functions (if needed)
    ADMIN_MENU = auto()
    ADMIN_USER_MANAGEMENT = auto()
    ADMIN_ANALYTICS = auto()


class UserContext:
    """Context data for user conversations."""
    
    def __init__(self):
        self.current_state: ConversationStates = ConversationStates.MAIN_MENU
        self.temp_data: dict = {}
        self.selected_child_id: str = None
        self.current_translation_id: str = None
        self.session_id: str = None
        
    def clear(self):
        """Clear temporary data while keeping session info."""
        self.temp_data = {}
        self.selected_child_id = None
        self.current_translation_id = None
    
    def set_state(self, state):
        """Set current conversation state."""
        if isinstance(state, str):
            self.current_state = state
        else:
            self.current_state = state
    
    def get_temp_data(self, key: str, default=None):
        """Get temporary data by key."""
        return self.temp_data.get(key, default)
    
    def set_temp_data(self, key: str, value):
        """Set temporary data."""
        self.temp_data[key] = value