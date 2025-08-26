"""Inline keyboards for Telegram bot."""
from typing import List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ...core.models.user import Children, UserRole
from ...core.localization import _


class InlineKeyboards:
    """Factory class for creating inline keyboards."""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Create main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('buttons.emotion_translate'), callback_data="emotion_translate"),
                InlineKeyboardButton(_('buttons.weekly_report'), callback_data="view_reports")
            ],
            [
                InlineKeyboardButton(_('buttons.manage_children'), callback_data="manage_children"),
                InlineKeyboardButton(_('buttons.manage_family'), callback_data="manage_family")
            ],
            [
                InlineKeyboardButton(_('buttons.settings'), callback_data="settings"),
                InlineKeyboardButton(_('buttons.help'), callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def child_management() -> InlineKeyboardMarkup:
        """Create child management keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('buttons.add_child'), callback_data="add_child"),
                InlineKeyboardButton(_('buttons.edit_child'), callback_data="edit_child")
            ],
            [
                InlineKeyboardButton(_('buttons.child_reports'), callback_data="child_reports"),
                InlineKeyboardButton(_('buttons.remove_child'), callback_data="remove_child")
            ],
            [
                InlineKeyboardButton(_('buttons.back_main_menu'), callback_data="main_menu")
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
                    f"👶 {child.name} ({child.age} {_('common.years')})", 
                    callback_data=f"{action}_child_{child.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(_('buttons.back'), callback_data="manage_children")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def emotion_translation_options() -> InlineKeyboardMarkup:
        """Create options for emotion translation."""
        keyboard = [
            [
                InlineKeyboardButton("🎯 Быстрый перевод", callback_data="emotion_quick"),
                InlineKeyboardButton("📝 Подробный анализ", callback_data="emotion_detailed")
            ],
            [
                InlineKeyboardButton("📚 Последние переводы", callback_data="emotion_history")
            ],
            [
                InlineKeyboardButton(_('buttons.back_main_menu'), callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def emotion_results_actions(translation_id: str) -> InlineKeyboardMarkup:
        """Create actions for emotion translation results."""
        keyboard = [
            [
                InlineKeyboardButton("📧 Поделиться результатами", callback_data=f"share_{translation_id}"),
                InlineKeyboardButton("💾 Сохранить в отчёт", callback_data=f"save_{translation_id}")
            ],
            [
                InlineKeyboardButton("🔄 Новый перевод", callback_data="emotion_translate"),
                InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")
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
            InlineKeyboardButton("🔙 К результатам", callback_data="back_to_results")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Create settings menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('settings.options.language'), callback_data="settings_language"),
                InlineKeyboardButton(_('settings.options.timezone'), callback_data="settings_timezone")
            ],
            [
                InlineKeyboardButton(_('settings.options.notifications'), callback_data="settings_notifications"),
                InlineKeyboardButton(_('settings.options.subscription'), callback_data="settings_subscription")
            ],
            [
                InlineKeyboardButton(_('settings.options.usage_stats'), callback_data="settings_usage"),
                InlineKeyboardButton(_('settings.options.delete_account'), callback_data="settings_delete")
            ],
            [
                InlineKeyboardButton(_('buttons.back_main_menu'), callback_data="main_menu")
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
                InlineKeyboardButton("🔙 К настройкам", callback_data="settings")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirmation(confirm_action: str, cancel_action: str = "main_menu") -> InlineKeyboardMarkup:
        """Create confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('buttons.confirm'), callback_data=confirm_action),
                InlineKeyboardButton(_('buttons.cancel'), callback_data=cancel_action)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def family_management() -> InlineKeyboardMarkup:
        """Create family management keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('family.actions.add_member'), callback_data="family_add"),
                InlineKeyboardButton(_('family.actions.view_members'), callback_data="family_list")
            ],
            [
                InlineKeyboardButton(_('family.actions.edit_permissions'), callback_data="family_permissions"),
                InlineKeyboardButton(_('family.actions.remove_member'), callback_data="family_remove")
            ],
            [
                InlineKeyboardButton(_('buttons.back_main_menu'), callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def user_role_selection() -> InlineKeyboardMarkup:
        """Create user role selection keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('family.roles.parent'), callback_data="role_parent"),
                InlineKeyboardButton(_('family.roles.caregiver'), callback_data="role_caregiver")
            ],
            [
                InlineKeyboardButton(_('buttons.back'), callback_data="manage_family")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def reports_menu() -> InlineKeyboardMarkup:
        """Create reports menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('reports.timeframes.this_week'), callback_data="report_week"),
                InlineKeyboardButton(_('reports.timeframes.this_month'), callback_data="report_month")
            ],
            [
                InlineKeyboardButton(_('reports.timeframes.custom'), callback_data="report_custom"),
                InlineKeyboardButton(_('reports.timeframes.trends'), callback_data="report_trends")
            ],
            [
                InlineKeyboardButton(_('reports.children_options.all'), callback_data="report_all"),
                InlineKeyboardButton(_('reports.children_options.specific'), callback_data="report_child_select")
            ],
            [
                InlineKeyboardButton(_('buttons.back_main_menu'), callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def help_menu() -> InlineKeyboardMarkup:
        """Create help menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🚀 Начало работы", callback_data="help_start"),
                InlineKeyboardButton("❓ Частые вопросы", callback_data="help_faq")
            ],
            [
                InlineKeyboardButton("💡 Советы и хитрости", callback_data="help_tips"),
                InlineKeyboardButton("📧 Обратиться в поддержку", callback_data="help_contact")
            ],
            [
                InlineKeyboardButton("🔄 Команды бота", callback_data="help_commands"),
                InlineKeyboardButton("🔒 Политика конфиденциальности", callback_data="help_privacy")
            ],
            [
                InlineKeyboardButton(_('buttons.back_main_menu'), callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def subscription_options() -> InlineKeyboardMarkup:
        """Create subscription options keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(_('settings.subscription_options.upgrade_premium'), callback_data="upgrade_premium"),
                InlineKeyboardButton(_('settings.subscription_options.current_usage'), callback_data="usage_stats")
            ],
            [
                InlineKeyboardButton(_('settings.subscription_options.billing_info'), callback_data="billing_info"),
                InlineKeyboardButton(_('settings.subscription_options.cancel_subscription'), callback_data="cancel_subscription")
            ],
            [
                InlineKeyboardButton("🔙 К настройкам", callback_data="settings")
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
                InlineKeyboardButton(_('buttons.skip'), callback_data="skip_optional"),
                InlineKeyboardButton(_('buttons.back'), callback_data="back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)