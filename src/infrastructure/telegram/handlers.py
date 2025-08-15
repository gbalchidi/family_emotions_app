"""Telegram bot handlers for all user interactions."""
from __future__ import annotations

import logging
from datetime import datetime, date
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
from ...core.models import UserRole
from ...core.exceptions import (
    RateLimitExceededError,
    ResourceNotFoundError, 
    ValidationError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    bot = context.bot_data['bot_instance']
    
    try:
        # Get or create user
        user_result = await bot.get_or_create_user(update)
        if not user_result:
            await bot.handle_error(update, context, "Failed to initialize user account")
            return
        
        user, is_new_user = user_result
        
        # Clear any existing context
        bot.clear_user_context(update.effective_user.id)
        user_context = bot.get_user_context(update.effective_user.id)
        user_context.set_state(ConversationStates.MAIN_MENU)
        
        # Send welcome message
        greeting = await bot.format_user_greeting(user, is_new_user)
        
        await update.message.reply_text(
            text=greeting,
            reply_markup=InlineKeyboards.main_menu(),
            parse_mode="HTML"
        )
        
        # Track start command usage
        await bot.analytics_service.track_event(
            event_type="bot_command_used",
            user_id=user.id,
            user_telegram_id=user.telegram_id,
            event_data={"command": "start", "is_new_user": is_new_user}
        )
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await bot.handle_error(update, context, "Failed to start bot")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    bot = context.bot_data['bot_instance']
    
    help_text = """
❓ <b>Family Emotions App Help</b>

🌟 <b>Main Features:</b>

<b>🎯 Emotion Translation</b>
Describe your child's behavior or words, and I'll help you understand their emotions and suggest appropriate responses.

<b>👶 Child Management</b>
Add your children's profiles with age, personality traits, and interests for more personalized analysis.

<b>📊 Weekly Reports</b>
Get comprehensive reports on your child's emotional development and patterns.

<b>👨‍👩‍👧‍👦 Family Sharing</b>
Add family members to share insights and collaborate on child care.

<b>⚙️ Settings</b>
Customize language, notifications, and account preferences.

📱 <b>Quick Commands:</b>
/start - Return to main menu
/help - Show this help message
/stats - View your usage statistics
/children - Quick access to child management
/translate - Start emotion translation

💡 <b>Tips:</b>
• Be specific when describing situations
• Add context about your child's personality
• Review weekly reports for insights
• Use family sharing for consistent responses

Need more help? Use the Help menu below! 👇
"""
    
    await update.message.reply_text(
        text=help_text,
        reply_markup=InlineKeyboards.help_menu(),
        parse_mode="HTML"
    )


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
            text = """
👶 <b>No children in your profile yet!</b>

Add your first child to get started with personalized emotion analysis.

Click "Add Child" below to begin! 👇
"""
        else:
            text = f"👶 <b>Your Children ({len(user.children)})</b>\n\n"
            for child in user.children:
                text += f"• {child.name} ({child.age} years)\n"
            
            text += "\nManage your children using the options below 👇"
        
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboards.child_management(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in children handler: {e}")
        await bot.handle_error(update, context, "Failed to load children")


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
            text = """
⚠️ <b>Add a child first</b>

To provide personalized emotion analysis, please add at least one child to your profile.

Click "Manage Children" below to get started! 👇
"""
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            return
        
        # Start emotion translation flow
        user_context.set_state(ConversationStates.EMOTION_SELECT_CHILD)
        
        text = """
🎯 <b>Emotion Translation</b>

Which child would you like to analyze?

Select a child below to continue 👇
"""
        
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboards.children_list(user.children, "translate"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in translate handler: {e}")
        await bot.handle_error(update, context, "Failed to start translation")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries from inline keyboards."""
    bot = context.bot_data['bot_instance']
    query = update.callback_query
    
    try:
        await query.answer()  # Acknowledge the callback
        
        user_result = await bot.get_or_create_user(update)
        if not user_result:
            return
        
        user, _ = user_result
        user_context = bot.get_user_context(update.effective_user.id)
        data = query.data
        
        # Route callback based on data
        if data == "main_menu":
            await handle_main_menu(query, bot, user)
            
        elif data == "emotion_translate":
            await handle_emotion_translate_start(query, bot, user, user_context)
            
        elif data.startswith("translate_child_"):
            child_id = data.replace("translate_child_", "")
            await handle_child_selection_for_translation(query, bot, user, user_context, child_id)
            
        elif data == "manage_children":
            await handle_child_management_menu(query, bot, user)
            
        elif data == "add_child":
            await handle_add_child_start(query, bot, user, user_context)
            
        elif data.startswith("edit_child_"):
            child_id = data.replace("edit_child_", "")
            await handle_edit_child(query, bot, user, child_id)
            
        elif data == "view_reports":
            await handle_reports_menu(query, bot, user)
            
        elif data == "settings":
            await handle_settings_menu(query, bot, user)
            
        elif data.startswith("settings_"):
            setting = data.replace("settings_", "")
            await handle_settings_option(query, bot, user, user_context, setting)
            
        elif data == "help":
            await handle_help_menu(query, bot, user)
            
        elif data.startswith("help_"):
            help_topic = data.replace("help_", "")
            await handle_help_topic(query, bot, help_topic)
            
        elif data == "manage_family":
            await handle_family_management(query, bot, user)
            
        else:
            # Handle unknown callback
            await query.edit_message_text(
                text="❌ Unknown action. Please try again.",
                reply_markup=InlineKeyboards.main_menu()
            )
        
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await bot.handle_error(update, context, "An error occurred processing your request")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on conversation state."""
    bot = context.bot_data['bot_instance']
    
    try:
        user_result = await bot.get_or_create_user(update)
        if not user_result:
            return
        
        user, _ = user_result
        user_context = bot.get_user_context(update.effective_user.id)
        
        current_state = user_context.current_state
        message_text = update.message.text
        
        # Route message based on conversation state
        if current_state == ConversationStates.ADD_CHILD_NAME:
            await handle_add_child_name(update, bot, user, user_context, message_text)
            
        elif current_state == ConversationStates.ADD_CHILD_AGE:
            await handle_add_child_age(update, bot, user, user_context, message_text)
            
        elif current_state == ConversationStates.ADD_CHILD_PERSONALITY:
            await handle_add_child_personality(update, bot, user, user_context, message_text)
            
        elif current_state == ConversationStates.ADD_CHILD_INTERESTS:
            await handle_add_child_interests(update, bot, user, user_context, message_text)
            
        elif current_state == ConversationStates.ADD_CHILD_SPECIAL_NEEDS:
            await handle_add_child_special_needs(update, bot, user, user_context, message_text)
            
        elif current_state == ConversationStates.EMOTION_ENTER_MESSAGE:
            await handle_emotion_message_input(update, bot, user, user_context, message_text)
            
        elif current_state == ConversationStates.EMOTION_ADD_CONTEXT:
            await handle_emotion_context_input(update, bot, user, user_context, message_text)
            
        else:
            # Default response for unexpected messages
            await update.message.reply_text(
                text="🤔 I'm not sure what you mean. Use the menu below to navigate:",
                reply_markup=InlineKeyboards.main_menu()
            )
        
    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        await bot.handle_error(update, context, "An error occurred processing your message")


# Individual handler functions for different actions

async def handle_main_menu(query, bot, user):
    """Handle main menu display."""
    greeting = f"👋 <b>Welcome, {user.first_name}!</b>\n\nWhat would you like to do today?"
    
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


async def handle_add_child_start(query, bot, user, user_context):
    """Start adding a new child."""
    user_context.clear()
    user_context.set_state(ConversationStates.ADD_CHILD_NAME)
    
    text = """
👶 <b>Add New Child</b>

What is your child's name?

<i>Type the name below:</i>
"""
    
    await query.edit_message_text(
        text=text,
        parse_mode="HTML"
    )


async def handle_add_child_name(update, bot, user, user_context, name):
    """Handle child name input."""
    if len(name.strip()) < 1:
        await update.message.reply_text(
            text="⚠️ Please enter a valid name for your child."
        )
        return
    
    user_context.set_temp_data("child_name", name.strip())
    user_context.set_state(ConversationStates.ADD_CHILD_AGE)
    
    text = f"""
👶 <b>Adding {name}</b>

How old is {name}? Please enter their age in years (0-18).

<i>Type the age below:</i>
"""
    
    await update.message.reply_text(
        text=text,
        parse_mode="HTML"
    )


async def handle_add_child_age(update, bot, user, user_context, age_text):
    """Handle child age input."""
    try:
        age = int(age_text.strip())
        if age < 0 or age > 18:
            await update.message.reply_text(
                text="⚠️ Please enter a valid age between 0 and 18 years."
            )
            return
        
        user_context.set_temp_data("child_age", age)
        user_context.set_state(ConversationStates.ADD_CHILD_PERSONALITY)
        
        name = user_context.get_temp_data("child_name")
        
        text = f"""
👶 <b>Adding {name} ({age} years)</b>

Tell me about {name}'s personality. This helps me provide better emotion analysis.

For example:
• "Shy and sensitive, loves books"
• "Energetic and outgoing, gets frustrated easily"
• "Creative and imaginative, sometimes anxious"

<i>Describe their personality below, or type "skip" to continue:</i>
"""
        
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboards.skip_optional(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await update.message.reply_text(
            text="⚠️ Please enter a valid number for the age."
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


def setup_handlers(bot):
    """Setup all handlers for the bot."""
    app = bot.application
    
    # Store bot instance in context for handlers
    app.bot_data['bot_instance'] = bot
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("children", children_handler))
    app.add_handler(CommandHandler("translate", translate_handler))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Message handler for conversation states
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("All handlers setup complete")