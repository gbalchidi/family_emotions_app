"""Telegram bot handlers for all user interactions."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from telegram import Update
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from .keyboards import InlineKeyboards
from .states import ConversationStates
from ...core.exceptions import (
    RateLimitExceededError
)
from ...core.localization import _, Language, set_language

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    try:
        logger.info(f"Start command from user {update.effective_user.id}")
        
        # Set language to Russian for target audience
        set_language(Language.RUSSIAN)
        
        # Provide localized welcome message
        welcome_text = f"""
👋 <b>{_('welcome.title', name=update.effective_user.first_name)}</b>

{_('welcome.description')}

🌟 <b>Что я умею:</b>
• {_('welcome.features.translate')}
• {_('welcome.features.suggestions')}
• {_('welcome.features.reports')}
• {_('welcome.features.tracking')}

{_('welcome.help_command')}

<i>{_('welcome.ready')}</i>
"""
        
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=InlineKeyboards.main_menu(),
            parse_mode="HTML"
        )
        
        # Try to create user in background (optional)
        bot = context.bot_data.get('bot_instance')
        logger.info(f"Bot instance available: {bot is not None}")
        
        if bot:
            logger.info(f"Database manager available: {bot.db_manager is not None}")
            if bot.db_manager:
                logger.info(f"Database manager type: {type(bot.db_manager)}")
            else:
                logger.warning(f"Bot.db_manager is None - bot instance: {type(bot)}")
            
        if bot and bot.db_manager:
            try:
                logger.info(f"Background user creation for {update.effective_user.id}")
                user_result = await bot.get_or_create_user(update)
                if user_result:
                    logger.info(f"User successfully created/found in database")
                else:
                    logger.warning("Database user creation returned None")
            except Exception as e:
                logger.warning(f"Background database operation failed: {e}", exc_info=True)
        else:
            logger.info("Skipping database operations - database manager not available")
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        # Even if everything fails, provide basic response
        try:
            await update.message.reply_text(
                text=f"👋 {_('common.hello')} {update.effective_user.first_name}! {_('common.welcome')} Family Emotions App.\n\n{_('welcome.help_command')}",
                parse_mode="HTML"
            )
        except:
            await update.message.reply_text(f"👋 {_('common.welcome')}! {_('welcome.help_command')}")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    try:
        logger.info(f"Help command from user {update.effective_user.id}")
        
        help_text = f"""
❓ <b>{_('help.title')}</b>

🌟 <b>Основные функции:</b>

<b>🎯 {_('help.features.emotion_translation.title')}</b>
{_('help.features.emotion_translation.description')}

<b>👶 {_('help.features.child_management.title')}</b>
{_('help.features.child_management.description')}

<b>📊 {_('help.features.weekly_reports.title')}</b>
{_('help.features.weekly_reports.description')}

📱 <b>{_('help.commands.title')}</b>
/start - {_('help.commands.start')}
/help - {_('help.commands.help')}
/settings - {_('help.commands.settings')}
/test - {_('help.commands.test')}

💡 <b>{_('help.tips.title')}</b>
• {_('help.tips.specific')}
• {_('help.tips.context')}
• {_('help.tips.sharing')}

{_('help.development_mode')}
"""
        
        await update.message.reply_text(
            text=help_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        await update.message.reply_text(f"❌ {_('errors.generic')}")


async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test command."""
    try:
        logger.info(f"Test command from user {update.effective_user.id}")
        
        await update.message.reply_text(
            text=f"✅ <b>{_('success.bot_working')}</b>\n\n{_('success.polling_active')}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in test handler: {e}")
        await update.message.reply_text(f"❌ {_('errors.test_failed')}")


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    bot = context.bot_data['bot_instance']
    
    try:
        user_result = await bot.get_or_create_user(update)
        if not user_result:
            return
        
        user, _ = user_result
        stats_text = await bot.format_usage_stats(user)
        
        await update.message.reply_text(
            text=stats_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in stats handler: {e}")
        await bot.handle_error(update, context, "Failed to retrieve statistics")


async def children_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /children command."""
    bot = context.bot_data['bot_instance']
    
    try:
        user_result = await bot.get_or_create_user(update)
        if not user_result:
            return
        
        user, _ = user_result
        
        if not user.children:
            text = f"""
👶 <b>{_('child_management.no_children.title')}</b>

{_('child_management.no_children.description')}

{_('child_management.no_children.cta')}
"""
        else:
            text = f"👶 <b>{_('child_management.children_list.title', count=len(user.children))}</b>\n\n"
            for child in user.children:
                text += f"• {child.name} ({child.age} {_('common.years')})\n"
            
            text += f"\n{_('child_management.children_list.manage_text')}"
        
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboards.child_management(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in children handler: {e}")
        await bot.handle_error(update, context, "Не удалось загрузить детей")


async def translate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /translate command."""
    bot = context.bot_data['bot_instance']
    
    try:
        user_result = await bot.get_or_create_user(update)
        if not user_result:
            return
        
        user, _ = user_result
        user_context = bot.get_user_context(update.effective_user.id)
        
        # Check if user has children
        if not user.children:
            text = f"""
⚠️ <b>{_('emotion_translation.no_children.title')}</b>

{_('emotion_translation.no_children.description')}

{_('emotion_translation.no_children.cta')}
"""
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            return
        
        # Start emotion translation flow
        user_context.set_state(ConversationStates.EMOTION_SELECT_CHILD)
        
        text = f"""
🎯 <b>{_('emotion_translation.select_child.title')}</b>

{_('emotion_translation.select_child.prompt')}

{_('emotion_translation.select_child.cta')}
"""
        
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboards.children_list(user.children, "translate"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in translate handler: {e}")
        await bot.handle_error(update, context, "Не удалось начать перевод")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries from inline keyboards."""
    query = update.callback_query
    bot = context.bot_data.get('bot_instance')
    
    try:
        await query.answer()  # Acknowledge the callback
        logger.info(f"Callback query: {query.data} from user {update.effective_user.id}")
        
        data = query.data
        
        # Handle basic callbacks
        if data == "main_menu":
            await query.edit_message_text(
                text=f"👋 <b>{_('common.welcome')}, {update.effective_user.first_name}!</b>\n\nЧто вы хотели бы сделать сегодня?",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        elif data == "manage_children":
            await query.edit_message_text(
                text=f"👶 <b>Управление детьми</b>\n\nУправляйте профилями ваших детей для персонализированного анализа эмоций.\n\n<i>Функция скоро появится...</i>",
                reply_markup=InlineKeyboards.child_management(),
                parse_mode="HTML"
            )
            
        elif data == "help":
            await query.edit_message_text(
                text=f"❓ <b>Помощь и поддержка</b>\n\nПолучите помощь по использованию Family Emotions App.\n\n<i>Полная система помощи скоро появится...</i>",
                reply_markup=InlineKeyboards.help_menu(),
                parse_mode="HTML"
            )
            
        elif data == "settings":
            await query.edit_message_text(
                text=f"⚙️ <b>{_('settings.title')}</b>\n\nНастройте предпочтения приложения.\n\n<i>Панель настроек скоро появится...</i>",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        elif data == "emotion_translate":
            # Start emotion translation flow
            await query.edit_message_text(
                text=f"🌟 <b>Перевод эмоций</b>\n\nОпишите, что сказал ваш ребенок или как он себя ведет. Будьте максимально конкретными.\n\n<b>Примеры:</b>\n• \"Мой сын сказал 'Я тебя ненавижу' и хлопнул дверью\"\n• \"Она очень тихая и не смотрит в глаза\"\n• \"Он бросает игрушки и громко плачет\"\n\n<i>Пожалуйста, введите описание ниже:</i>",
                parse_mode="HTML"
            )
            
            # Set conversation state for emotion translation
            if bot:
                user_context = bot.get_user_context(update.effective_user.id)
                user_context.current_state = "EMOTION_TRANSLATE_INPUT"
            
        elif data == "view_reports":
            await query.edit_message_text(
                text=f"📊 <b>{_('reports.title')}</b>\n\n{_('reports.description')}\n\n<i>{_('reports.coming_soon')}</i>",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        elif data == "manage_family":
            await query.edit_message_text(
                text=f"👨‍👩‍👧‍👦 <b>{_('family.title')}</b>\n\n{_('family.description')}\n\n<i>{_('family.coming_soon')}</i>",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        elif data == "add_child":
            # Start add child flow
            await query.edit_message_text(
                text="👶 <b>Add New Child</b>\n\nWhat is your child's name?\n\n<i>Please type the name below:</i>",
                parse_mode="HTML"
            )
            
            # Set conversation state for this user
            if bot:
                user_context = bot.get_user_context(update.effective_user.id)
                user_context.current_state = "ADD_CHILD_NAME"
            
        else:
            # Handle unknown callback
            await query.edit_message_text(
                text="❌ Unknown action. Please try again.",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        try:
            await query.edit_message_text(
                text="❌ An error occurred. Please try again.",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
        except:
            pass


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on conversation state."""
    try:
        logger.info(f"Message from user {update.effective_user.id}: {update.message.text}")
        
        bot = context.bot_data.get('bot_instance')
        if not bot:
            await update.message.reply_text(
                text=f"🤔 Я не понимаю, что вы имеете в виду. Нажмите /start, чтобы начать!"
            )
            return
        
        user_context = bot.get_user_context(update.effective_user.id)
        current_state = getattr(user_context, 'current_state', None)
        message_text = update.message.text
        
        logger.info(f"Current state: {current_state}")
        
        # Get user for consistent function signatures (with fallback for database issues)
        user_result = await bot.get_or_create_user(update)
        if not user_result:
            # Database is unavailable, create a temporary user object for basic functionality
            from types import SimpleNamespace
            user = SimpleNamespace(
                id=f"temp_{update.effective_user.id}",
                telegram_id=update.effective_user.id,
                first_name=update.effective_user.first_name,
                children=[]
            )
            logger.info(f"Using temporary user object for {update.effective_user.id} due to database unavailability")
        else:
            user, _ = user_result
        
        # Route message based on conversation state  
        if current_state == "ADD_CHILD_NAME":
            logger.info(f"Calling handle_add_child_name with consistent 5-arg signature")
            await handle_add_child_name(update, bot, user, user_context, message_text)
            
        elif current_state == "ADD_CHILD_AGE":
            await handle_add_child_age(update, bot, user, user_context, message_text)
            
        elif current_state == "EMOTION_TRANSLATE_INPUT":
            await handle_emotion_translate_input(update, bot, message_text)
            
        else:
            # Default response for unexpected messages
            await update.message.reply_text(
                text=f"🤔 Я не понимаю, что вы имеете в виду. Используйте меню ниже для навигации:",
                reply_markup=InlineKeyboards.main_menu()
            )
        
    except Exception as e:
        logger.error(f"Error in message handler: {e}", exc_info=True)
        await update.message.reply_text(f"❌ {_('errors.processing_failed')}")


# Individual handler functions for different actions

async def handle_add_child_name(update: Update, bot, user, user_context, name: str):
    """Handle child name input. CONSISTENT SIGNATURE - 5 parameters including user."""
    logger.info(f"Handle add child name called with name: {name}")
    try:
        if len(name.strip()) < 1:
            await update.message.reply_text(
                text=f"⚠️ {_('validation.name_required')}"
            )
            return
        
        user_context.temp_data["child_name"] = name.strip()
        user_context.current_state = "ADD_CHILD_AGE"
        
        await update.message.reply_text(
            text=f"👶 <b>Добавляем {name}</b>\n\n{_('child_management.add_child.age_prompt', name=name)}\n\n<i>{_('child_management.add_child.age_input')}</i>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error handling child name: {e}")
        await update.message.reply_text(f"❌ {_('errors.something_wrong')}")


async def handle_add_child_age(update: Update, bot, user, user_context, age_text: str):
    """Handle child age input. CONSISTENT SIGNATURE - 5 parameters including user."""
    try:
        age = int(age_text.strip())
        if age < 0 or age > 18:
            await update.message.reply_text(
                text=f"⚠️ {_('validation.age_invalid')}"
            )
            return
        
        name = user_context.temp_data.get("child_name", "Unknown")
        user_context.temp_data["child_age"] = age
        user_context.current_state = None  # Reset state
        
        # Complete the process with Russian text
        success_text = f"""
✅ <b>{_('child_management.add_child.success.title')}</b>

{_('child_management.add_child.success.profile', name=name, age=age)}

{_('child_management.add_child.success.completion', name=name)}

{_('child_management.add_child.success.next_steps')}
"""
        
        await update.message.reply_text(
            text=success_text,
            reply_markup=InlineKeyboards.main_menu(),
            parse_mode="HTML"
        )
        
        logger.info(f"Child {name} ({age}) added successfully")
        
    except ValueError:
        await update.message.reply_text(
            text=f"⚠️ {_('validation.age_number')}"
        )
    except Exception as e:
        logger.error(f"Error handling child age: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")


async def handle_emotion_translate_input(update: Update, bot, message_text: str):
    """Handle emotion translation input with Claude API."""
    try:
        user_context = bot.get_user_context(update.effective_user.id)
        user_context.current_state = None  # Reset state
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            text=f"🔄 <b>{_('emotion_translation.processing.title')}</b>\n\n{_('emotion_translation.processing.description')}",
            parse_mode="HTML"
        )
        
        try:
            # Call Claude API for emotion analysis
            from anthropic import Anthropic
            from src.core.config import settings
            
            # Debug API key (mask most of it for security)
            api_key = settings.anthropic.claude_api_key
            if api_key:
                masked_key = api_key[:10] + "***" + api_key[-4:] if len(api_key) > 14 else "***MASKED***"
                logger.info(f"Using Claude API key: {masked_key}")
            else:
                logger.error("Claude API key is None or empty!")
                
            # Try to debug the API call
            logger.info(f"Creating Anthropic client with model: {settings.anthropic.model}")
            
            # Try with different base URLs in case of regional restrictions
            base_urls_to_try = [
                None,  # Default
                "https://api.anthropic.com",  # Explicit default
                "https://claude.ai/api",  # Alternative endpoint
            ]
            
            # For now, just create default client - multiple base URLs don't help with 403 errors
            client = Anthropic(api_key=api_key)
            
            prompt = f"""You are an expert child psychologist helping parents understand their child's emotions. 

Analyze this situation and provide:
1. What emotions the child is likely experiencing
2. Possible reasons behind these emotions
3. 3 specific, age-appropriate response suggestions

Situation: "{message_text}"

Respond in this format:
**Emotions detected:** [list emotions]
**Possible reasons:** [brief explanation]
**Suggested responses:**
1. [First response approach]
2. [Second response approach] 
3. [Third response approach]

Keep responses practical, empathetic, and focused on connection with the child."""

            logger.info("Making Claude API request...")
            response = client.messages.create(
                model=settings.anthropic.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            logger.info(f"Claude API response received, length: {len(response.content[0].text) if response.content else 0}")
            
            result_text = f"""
🎯 <b>{_('emotion_translation.result.title')}</b>

📝 <b>{_('emotion_translation.result.situation')}</b>
<i>"{message_text}"</i>

{response.content[0].text}

💡 <b>Помните:</b> {_('emotion_translation.result.remember')}

{_('emotion_translation.result.next_steps')}
"""
            
            await processing_msg.edit_text(
                text=result_text,
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
            logger.info(f"Emotion translation completed for user {update.effective_user.id}")
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error calling Claude API: {e}")
            
            # Check if it's a 403 forbidden error
            if "403" in error_message or "forbidden" in error_message.lower():
                logger.warning("Claude API returning 403 Forbidden - likely IP/region restriction or API key issue")
            
            # Provide fallback emotional analysis without Claude API
            fallback_analysis = f"""
🎯 <b>{_('emotion_translation.fallback.title')}</b>

📝 <b>{_('emotion_translation.result.situation')}</b>
<i>"{message_text}"</i>

**Обнаруженные эмоции:** {_('emotion_translation.fallback.emotions')}

**Возможные причины:** {_('emotion_translation.fallback.reasons')}

**Предлагаемые ответы:**
1. {_('emotion_translation.fallback.responses.listen')}
2. {_('emotion_translation.fallback.responses.validate')}
3. {_('emotion_translation.fallback.responses.boundaries')}

💡 <b>Помните:</b> {_('emotion_translation.result.remember')}

<i>{_('emotion_translation.fallback.note')}</i>

{_('emotion_translation.result.next_steps')}
"""
            
            await processing_msg.edit_text(
                text=fallback_analysis,
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in emotion translation: {e}")
        await update.message.reply_text(f"❌ {_('errors.something_wrong')}")

async def handle_main_menu(query, bot, user):
    """Handle main menu display."""
    greeting = f"👋 <b>{_('common.welcome')}, {user.first_name}!</b>\n\nЧто вы хотите сделать сегодня?"
    
    await query.edit_message_text(
        text=greeting,
        reply_markup=InlineKeyboards.main_menu(),
        parse_mode="HTML"
    )


async def handle_emotion_translate_start(query, bot, user, user_context):
    """Start emotion translation flow."""
    if not user.children:
        text = """
⚠️ <b>Add a child first</b>

To provide personalized emotion analysis, please add at least one child to your profile.

Click "Manage Children" below to get started! 👇
"""
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboards.main_menu(),
            parse_mode="HTML"
        )
        return
    
    user_context.set_state(ConversationStates.EMOTION_SELECT_CHILD)
    
    text = """
🎯 <b>Emotion Translation</b>

Which child would you like to analyze?

Select a child below to continue 👇
"""
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.children_list(user.children, "translate"),
        parse_mode="HTML"
    )


async def handle_child_selection_for_translation(query, bot, user, user_context, child_id):
    """Handle child selection for emotion translation."""
    try:
        # Find the selected child
        child = None
        for c in user.children:
            if str(c.id) == child_id:
                child = c
                break
        
        if not child:
            await query.edit_message_text(
                text="❌ Child not found. Please try again.",
                reply_markup=InlineKeyboards.main_menu()
            )
            return
        
        user_context.selected_child_id = child_id
        user_context.set_state(ConversationStates.EMOTION_ENTER_MESSAGE)
        
        text = f"""
🎯 <b>Analyzing emotions for {child.name}</b>

Please describe what {child.name} said, did, or how they're behaving. Be as specific as possible.

For example:
• "My son said 'I hate you' and slammed his door"
• "She's been very quiet and won't make eye contact"
• "He's throwing toys and crying loudly"

<i>Type your message below:</i> 👇
"""
        
        await query.edit_message_text(
            text=text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error handling child selection: {e}")
        await bot.handle_error(query, None, "Error selecting child")


async def handle_emotion_message_input(update, bot, user, user_context, message_text):
    """Handle emotion message input from user."""
    try:
        # Store the message
        user_context.set_temp_data("emotion_message", message_text)
        user_context.set_state(ConversationStates.EMOTION_ADD_CONTEXT)
        
        # Get selected child
        child_id = user_context.selected_child_id
        child = None
        for c in user.children:
            if str(c.id) == child_id:
                child = c
                break
        
        if not child:
            await update.message.reply_text(
                text="❌ Error: Child not found. Please start again.",
                reply_markup=InlineKeyboards.main_menu()
            )
            return
        
        text = f"""
📝 <b>Message recorded for {child.name}:</b>
<i>"{message_text}"</i>

Would you like to add any additional context about the situation? This helps me provide better analysis.

For example:
• What happened before this?
• Where did this occur?
• Was anyone else involved?
• Any special circumstances?

<b>Type additional context or send "skip" to continue:</b>
"""
        
        await update.message.reply_text(
            text=text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error handling emotion message: {e}")
        await bot.handle_error(update, None, "Error processing message")


async def handle_emotion_context_input(update, bot, user, user_context, message_text):
    """Handle additional context input and process emotion translation."""
    try:
        await bot.send_typing_action(update.message.chat)
        
        # Get data from context
        emotion_message = user_context.get_temp_data("emotion_message")
        child_id = user_context.selected_child_id
        
        # Add context if provided
        situation_context = None
        if message_text.lower() != "skip":
            situation_context = message_text
        
        # Process the emotion translation
        processing_msg = await update.message.reply_text(
            text="🔄 <b>Analyzing emotions...</b>\n\nThis may take a few seconds.",
            parse_mode="HTML"
        )
        
        try:
            # Create emotion translation
            translation = await bot.emotion_service.create_emotion_translation(
                user_id=user.id,
                child_message=emotion_message,
                child_id=UUID(child_id),
                situation_context=situation_context
            )
            
            # Get child for display
            child = None
            for c in user.children:
                if str(c.id) == child_id:
                    child = c
                    break
            
            # Format and send results
            result_text = await bot.format_emotion_translation_result(
                translation, 
                child.name if child else "your child"
            )
            
            await processing_msg.edit_text(
                text=result_text,
                reply_markup=InlineKeyboards.emotion_results_actions(str(translation.id)),
                parse_mode="HTML"
            )
            
            # Clear context
            user_context.clear()
            user_context.set_state(ConversationStates.MAIN_MENU)
            
        except RateLimitExceededError:
            await processing_msg.edit_text(
                text="⏳ <b>Daily limit reached</b>\n\nYou've used all your daily translations. Upgrade to Premium for more requests!",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Error processing translation: {e}")
            await processing_msg.edit_text(
                text="❌ <b>Translation failed</b>\n\nPlease try again later or contact support if the problem persists.",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error handling emotion context: {e}")
        await bot.handle_error(update, None, "Error processing emotion analysis")


# Child management handlers

async def handle_child_management_menu(query, bot, user):
    """Handle child management menu."""
    if not user.children:
        text = """
👶 <b>Child Management</b>

You haven't added any children yet. Add your first child to get started with personalized emotion analysis!

Click "Add Child" below to begin 👇
"""
    else:
        text = f"""
👶 <b>Child Management</b>

You have {len(user.children)} child(ren) in your profile:

"""
        for child in user.children:
            text += f"• {child.name} ({child.age} years)\n"
        
        text += "\nWhat would you like to do? 👇"
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.child_management(),
        parse_mode="HTML"
    )


async def handle_add_child_start(update, bot, user, user_context):
    """Start adding a new child. CONSISTENT SIGNATURE - uses update parameter."""
    user_context.clear()
    user_context.set_state(ConversationStates.ADD_CHILD_NAME)
    
    text = """
👶 <b>Add New Child</b>

What is your child's name?

<i>Type the name below:</i>
"""
    
    # Handle both query and update objects
    if hasattr(update, 'edit_message_text'):
        await update.edit_message_text(
            text=text,
            parse_mode="HTML"
        )
    elif hasattr(update, 'message'):
        await update.message.reply_text(
            text=text,
            parse_mode="HTML"
        )


async def handle_add_child_personality(update, bot, user, user_context, personality):
    """Handle child personality input."""
    if personality.lower() != "skip":
        user_context.set_temp_data("child_personality", personality)
    
    user_context.set_state(ConversationStates.ADD_CHILD_INTERESTS)
    name = user_context.get_temp_data("child_name")
    
    text = f"""
👶 <b>Adding {name}</b>

What are {name}'s main interests and hobbies? This helps me suggest more relevant responses.

For example:
• "Loves dinosaurs, drawing, and video games"
• "Enjoys dancing, music, and playing with dolls"
• "Interested in sports, especially soccer and basketball"

<i>List their interests below, or type "skip" to continue:</i>
"""
    
    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboards.skip_optional(),
        parse_mode="HTML"
    )


async def handle_add_child_interests(update, bot, user, user_context, interests):
    """Handle child interests input."""
    if interests.lower() != "skip":
        user_context.set_temp_data("child_interests", interests)
    
    user_context.set_state(ConversationStates.ADD_CHILD_SPECIAL_NEEDS)
    name = user_context.get_temp_data("child_name")
    
    text = f"""
👶 <b>Adding {name}</b>

Are there any special considerations I should know about {name}? This could include:

• Learning differences or challenges
• Medical conditions that affect behavior
• Therapy or treatment programs
• Communication preferences
• Sensory sensitivities

<i>Add special considerations below, or type "skip" to finish:</i>
"""
    
    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboards.skip_optional(),
        parse_mode="HTML"
    )


async def handle_add_child_special_needs(update, bot, user, user_context, special_needs):
    """Handle special needs input and create the child."""
    try:
        await bot.send_typing_action(update.message.chat)
        
        # Collect all data
        name = user_context.get_temp_data("child_name")
        age = user_context.get_temp_data("child_age")
        personality = user_context.get_temp_data("child_personality")
        interests = user_context.get_temp_data("child_interests")
        special_considerations = special_needs if special_needs.lower() != "skip" else None
        
        # Create the child
        child = await bot.family_service.add_child(
            parent_id=user.id,
            name=name,
            age=age,
            personality_traits=personality,
            interests=interests,
            special_needs=special_considerations
        )
        
        # Track child creation
        await bot.analytics_service.track_event(
            event_type="child_added",
            user_id=user.id,
            user_telegram_id=user.telegram_id,
            event_data={
                "child_id": str(child.id),
                "child_age": age,
                "has_personality": bool(personality),
                "has_interests": bool(interests),
                "has_special_needs": bool(special_considerations)
            }
        )
        
        # Format success message
        child_profile = await bot.format_child_profile(child)
        
        success_text = f"""
✅ <b>Child Added Successfully!</b>

{child_profile}

{name} has been added to your family profile. You can now get personalized emotion translations and analysis!

What would you like to do next? 👇
"""
        
        await update.message.reply_text(
            text=success_text,
            reply_markup=InlineKeyboards.main_menu(),
            parse_mode="HTML"
        )
        
        # Clear context
        user_context.clear()
        user_context.set_state(ConversationStates.MAIN_MENU)
        
    except Exception as e:
        logger.error(f"Error creating child: {e}")
        await bot.handle_error(update, None, "Failed to add child. Please try again.")


# Settings and other handlers

async def handle_settings_menu(query, bot, user):
    """Handle settings menu."""
    text = f"""
⚙️ <b>Settings</b>

<b>Account:</b> {user.first_name}
<b>Language:</b> {user.language_code.upper()}
<b>Subscription:</b> {user.subscription_status.value.title()}
<b>Daily Usage:</b> {user.daily_requests_count}/{'50' if user.subscription_status.value == 'premium' else '5'}

What would you like to configure? 👇
"""
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.settings_menu(),
        parse_mode="HTML"
    )


async def handle_reports_menu(query, bot, user):
    """Handle reports menu."""
    text = """
📊 <b>Weekly Reports</b>

View comprehensive emotional development reports for your children.

Choose a timeframe or child below 👇
"""
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.reports_menu(),
        parse_mode="HTML"
    )


async def handle_help_menu(query, bot, user):
    """Handle help menu."""
    text = """
❓ <b>Help & Support</b>

Get help with using the Family Emotions App and understanding your child's emotional development.

What do you need help with? 👇
"""
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.help_menu(),
        parse_mode="HTML"
    )


async def handle_family_management(query, bot, user):
    """Handle family management menu."""
    text = f"""
👨‍👩‍👧‍👦 <b>Family Members</b>

Share insights with family members and collaborate on child care.

<b>Current Members:</b> {len(user.family_members)} + You

What would you like to do? 👇
"""
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboards.family_management(),
        parse_mode="HTML"
    )


def setup_handlers(app_or_bot):
    """Setup all handlers for the bot."""
    # Handle both Application object and bot object with .application attribute
    if hasattr(app_or_bot, 'application'):
        app = app_or_bot.application
    else:
        app = app_or_bot
    
    # Store bot instance in context for handlers
    # We need to pass the actual FamilyEmotionsBot instance, not the Telegram bot
    # This will be set by the calling code in main.py
    if not app.bot_data.get('bot_instance'):
        logger.warning("Bot instance not set in bot_data - handlers may not work correctly")
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("test", test_handler))
    
    # Callback query handler for inline keyboards
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Message handler for conversation states
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("All handlers setup complete")