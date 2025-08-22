"""Inline keyboards for Telegram bot."""
from typing import List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ...core.models.user import Children, UserRole


class InlineKeyboards:
    """Factory class for creating inline keyboards."""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Create main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🌟 Translate Emotions", callback_data="emotion_translate"),
                InlineKeyboardButton("📊 Weekly Report", callback_data="view_reports")
            ],
            [
                InlineKeyboardButton("👶 Manage Children", callback_data="manage_children"),
                InlineKeyboardButton("👨‍👩‍👧‍👦 Family Members", callback_data="manage_family")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def child_management() -> InlineKeyboardMarkup:
        """Create child management keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Child", callback_data="add_child"),
                InlineKeyboardButton("📝 Edit Child", callback_data="edit_child")
            ],
            [
                InlineKeyboardButton("📈 Child Reports", callback_data="child_reports"),
                InlineKeyboardButton("🗑️ Remove Child", callback_data="remove_child")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def children_list(children: List[Children], action: str = "select") -> InlineKeyboardMarkup:
        """Create keyboard with list of children."""
        keyboard = []
        
        for child in children:
            keyboard.append([
                InlineKeyboardButton(
                    f"👶 {child.name} ({child.age} years)", 
                    callback_data=f"{action}_child_{child.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back", callback_data="manage_children")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def emotion_translation_options() -> InlineKeyboardMarkup:
        """Create options for emotion translation."""
        keyboard = [
            [
                InlineKeyboardButton("🎯 Quick Translation", callback_data="emotion_quick"),
                InlineKeyboardButton("📝 Detailed Analysis", callback_data="emotion_detailed")
            ],
            [
                InlineKeyboardButton("📚 Recent Translations", callback_data="emotion_history")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def emotion_results_actions(translation_id: str) -> InlineKeyboardMarkup:
        """Create actions for emotion translation results."""
        keyboard = [
            [
                InlineKeyboardButton("📧 Share Results", callback_data=f"share_{translation_id}"),
                InlineKeyboardButton("💾 Save to Report", callback_data=f"save_{translation_id}")
            ],
            [
                InlineKeyboardButton("🔄 New Translation", callback_data="emotion_translate"),
                InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def response_options(responses: List[dict]) -> InlineKeyboardMarkup:
        """Create keyboard for response options."""
        keyboard = []
        
        for i, response in enumerate(responses):
            keyboard.append([
                InlineKeyboardButton(
                    f"💡 {response['title']}", 
                    callback_data=f"response_option_{i}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Results", callback_data="back_to_results")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Create settings menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🌐 Language", callback_data="settings_language"),
                InlineKeyboardButton("⏰ Timezone", callback_data="settings_timezone")
            ],
            [
                InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
                InlineKeyboardButton("💳 Subscription", callback_data="settings_subscription")
            ],
            [
                InlineKeyboardButton("📊 Usage Stats", callback_data="settings_usage"),
                InlineKeyboardButton("🗑️ Delete Account", callback_data="settings_delete")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def language_selection() -> InlineKeyboardMarkup:
        """Create language selection keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
            ],
            [
                InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
                InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr")
            ],
            [
                InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
                InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh")
            ],
            [
                InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirmation(confirm_action: str, cancel_action: str = "main_menu") -> InlineKeyboardMarkup:
        """Create confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=confirm_action),
                InlineKeyboardButton("❌ Cancel", callback_data=cancel_action)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def family_management() -> InlineKeyboardMarkup:
        """Create family management keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Family Member", callback_data="family_add"),
                InlineKeyboardButton("👥 View Members", callback_data="family_list")
            ],
            [
                InlineKeyboardButton("✏️ Edit Permissions", callback_data="family_permissions"),
                InlineKeyboardButton("🗑️ Remove Member", callback_data="family_remove")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def user_role_selection() -> InlineKeyboardMarkup:
        """Create user role selection keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("👨‍👩‍👧‍👦 Parent", callback_data="role_parent"),
                InlineKeyboardButton("🧑‍🍼 Caregiver", callback_data="role_caregiver")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="manage_family")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def reports_menu() -> InlineKeyboardMarkup:
        """Create reports menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📅 This Week", callback_data="report_week"),
                InlineKeyboardButton("📆 This Month", callback_data="report_month")
            ],
            [
                InlineKeyboardButton("📊 Custom Range", callback_data="report_custom"),
                InlineKeyboardButton("📈 Trends", callback_data="report_trends")
            ],
            [
                InlineKeyboardButton("📋 All Children", callback_data="report_all"),
                InlineKeyboardButton("👶 Specific Child", callback_data="report_child_select")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def help_menu() -> InlineKeyboardMarkup:
        """Create help menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🚀 Getting Started", callback_data="help_start"),
                InlineKeyboardButton("❓ FAQ", callback_data="help_faq")
            ],
            [
                InlineKeyboardButton("💡 Tips & Tricks", callback_data="help_tips"),
                InlineKeyboardButton("📧 Contact Support", callback_data="help_contact")
            ],
            [
                InlineKeyboardButton("🔄 Bot Commands", callback_data="help_commands"),
                InlineKeyboardButton("🔒 Privacy Policy", callback_data="help_privacy")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def subscription_options() -> InlineKeyboardMarkup:
        """Create subscription options keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("⭐ Upgrade to Premium", callback_data="upgrade_premium"),
                InlineKeyboardButton("📊 Current Usage", callback_data="usage_stats")
            ],
            [
                InlineKeyboardButton("💳 Billing Info", callback_data="billing_info"),
                InlineKeyboardButton("❌ Cancel Subscription", callback_data="cancel_subscription")
            ],
            [
                InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def checkin_response_scale() -> InlineKeyboardMarkup:
        """Create mood scale for check-in responses."""
        keyboard = [
            [
                InlineKeyboardButton("😢 1", callback_data="mood_1"),
                InlineKeyboardButton("😞 2", callback_data="mood_2"),
                InlineKeyboardButton("😐 3", callback_data="mood_3"),
                InlineKeyboardButton("😊 4", callback_data="mood_4"),
                InlineKeyboardButton("😄 5", callback_data="mood_5")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def gender_selection() -> InlineKeyboardMarkup:
        """Create gender selection keyboard for child registration."""
        keyboard = [
            [
                InlineKeyboardButton("👦 Boy", callback_data="gender_boy"),
                InlineKeyboardButton("👧 Girl", callback_data="gender_girl")
            ],
            [
                InlineKeyboardButton("🤷 Prefer not to say", callback_data="gender_none"),
                InlineKeyboardButton("⏭️ Skip", callback_data="skip_gender")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def skip_optional() -> InlineKeyboardMarkup:
        """Create skip button for optional fields."""
        keyboard = [
            [
                InlineKeyboardButton("⏭️ Skip this step", callback_data="skip_optional"),
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)