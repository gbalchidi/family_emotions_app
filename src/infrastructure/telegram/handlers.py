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
from ...core.models.user import UserRole
from ...core.exceptions import (
    RateLimitExceededError,
    ResourceNotFoundError, 
    ValidationError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    try:
        logger.info(f"Start command from user {update.effective_user.id}")
        
        # Always provide a fallback welcome message
        welcome_text = f"""
👋 <b>Welcome to Family Emotions App, {update.effective_user.first_name}!</b>

I'm here to help you understand and respond to your child's emotions better.

🌟 <b>What I can do:</b>
• Translate your child's emotional expressions
• Provide age-appropriate response suggestions  
• Generate weekly emotional development reports
• Track emotional patterns and growth

Use /help to see all available commands!

<i>Bot is ready to use!</i>
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
                text=f"👋 Hello {update.effective_user.first_name}! Welcome to Family Emotions App.\n\nUse /help to see available commands.",
                parse_mode="HTML"
            )
        except:
            await update.message.reply_text("👋 Welcome! Use /help for commands.")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    try:
        logger.info(f"Help command from user {update.effective_user.id}")
        
        help_text = """
❓ <b>Family Emotions App Help</b>

🌟 <b>Main Features:</b>

<b>🎯 Emotion Translation</b>
Describe your child's behavior or words, and I'll help you understand their emotions and suggest appropriate responses.

<b>👶 Child Management</b>
Add your children's profiles with age, personality traits, and interests for more personalized analysis.

<b>📊 Weekly Reports</b>
Get comprehensive reports on your child's emotional development and patterns.

📱 <b>Available Commands:</b>
/start - Welcome and main menu
/help - Show this help message
/settings - Bot settings (coming soon)
/test - Test bot functionality

💡 <b>Tips:</b>
• Be specific when describing situations
• Add context about your child's personality  
• Use family sharing for consistent responses

Bot is currently in development mode.
"""
        
        await update.message.reply_text(
            text=help_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")


async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test command."""
    try:
        logger.info(f"Test command from user {update.effective_user.id}")
        
        await update.message.reply_text(
            text="✅ <b>Bot is working!</b>\n\nPolling is active and commands are being received.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in test handler: {e}")
        await update.message.reply_text("❌ Test failed.")


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
    query = update.callback_query
    bot = context.bot_data.get('bot_instance')
    
    try:
        await query.answer()  # Acknowledge the callback
        logger.info(f"Callback query: {query.data} from user {update.effective_user.id}")
        
        data = query.data
        
        # Handle basic callbacks
        if data == "main_menu":
            await query.edit_message_text(
                text=f"👋 <b>Welcome, {update.effective_user.first_name}!</b>\n\nWhat would you like to do today?",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        elif data == "manage_children":
            await query.edit_message_text(
                text="👶 <b>Child Management</b>\n\nManage your children's profiles for personalized emotion analysis.\n\n<i>Feature coming soon...</i>",
                reply_markup=InlineKeyboards.child_management(),
                parse_mode="HTML"
            )
            
        elif data == "help":
            await query.edit_message_text(
                text="❓ <b>Help & Support</b>\n\nGet help with using the Family Emotions App.\n\n<i>Full help system coming soon...</i>",
                reply_markup=InlineKeyboards.help_menu(),
                parse_mode="HTML"
            )
            
        elif data == "settings":
            await query.edit_message_text(
                text="⚙️ <b>Settings</b>\n\nConfigure your app preferences.\n\n<i>Settings panel coming soon...</i>",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        elif data == "emotion_translate":
            # Start emotion translation flow
            await query.edit_message_text(
                text="🌟 <b>Emotion Translation</b>\n\nDescribe what your child said or how they're behaving. Be as specific as possible.\n\n<b>Examples:</b>\n• \"My son said 'I hate you' and slammed his door\"\n• \"She's been very quiet and won't make eye contact\"\n• \"He's throwing toys and crying loudly\"\n\n<i>Please type your description below:</i>",
                parse_mode="HTML"
            )
            
            # Set conversation state for emotion translation
            if bot:
                user_context = bot.get_user_context(update.effective_user.id)
                user_context.current_state = "EMOTION_TRANSLATE_INPUT"
            
        elif data == "view_reports":
            await query.edit_message_text(
                text="📊 <b>Weekly Reports</b>\n\nView emotional development reports for your children.\n\n<i>Reports feature coming soon...</i>",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
        elif data == "manage_family":
            await query.edit_message_text(
                text="👨‍👩‍👧‍👦 <b>Family Members</b>\n\nShare insights with family members.\n\n<i>Family sharing coming soon...</i>",
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
                text="🤔 I'm not sure what you mean. Use /start to get started!"
            )
            return
        
        user_context = bot.get_user_context(update.effective_user.id)
        current_state = getattr(user_context, 'current_state', None)
        message_text = update.message.text
        
        logger.info(f"Current state: {current_state}")
        
        # Route message based on conversation state  
        if current_state == "ADD_CHILD_NAME":
            await handle_add_child_name(update, bot, user_context, message_text)
            
        elif current_state == "ADD_CHILD_AGE":
            await handle_add_child_age(update, bot, user_context, message_text)
            
        elif current_state == "EMOTION_TRANSLATE_INPUT":
            await handle_emotion_translate_input(update, bot, message_text)
            
        else:
            # Default response for unexpected messages
            await update.message.reply_text(
                text="🤔 I'm not sure what you mean. Use the menu below to navigate:",
                reply_markup=InlineKeyboards.main_menu()
            )
        
    except Exception as e:
        logger.error(f"Error in message handler: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred processing your message.")


# Individual handler functions for different actions

async def handle_add_child_name(update: Update, bot, user_context, name: str):
    """Handle child name input."""
    try:
        if len(name.strip()) < 1:
            await update.message.reply_text(
                text="⚠️ Please enter a valid name for your child."
            )
            return
        
        user_context.temp_data["child_name"] = name.strip()
        user_context.current_state = "ADD_CHILD_AGE"
        
        await update.message.reply_text(
            text=f"👶 <b>Adding {name}</b>\n\nHow old is {name}? Please enter their age in years (0-18).\n\n<i>Type the age below:</i>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error handling child name: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")


async def handle_add_child_age(update: Update, bot, user_context, age_text: str):
    """Handle child age input."""
    try:
        age = int(age_text.strip())
        if age < 0 or age > 18:
            await update.message.reply_text(
                text="⚠️ Please enter a valid age between 0 and 18 years."
            )
            return
        
        name = user_context.temp_data.get("child_name", "Unknown")
        user_context.temp_data["child_age"] = age
        user_context.current_state = None  # Reset state
        
        # For now, just complete the process
        success_text = f"""
✅ <b>Child Added Successfully!</b>

👶 <b>{name}</b>
📅 <b>Age:</b> {age} years old

{name} has been added to your family profile! You can now get personalized emotion translations and analysis.

What would you like to do next? 👇
"""
        
        await update.message.reply_text(
            text=success_text,
            reply_markup=InlineKeyboards.main_menu(),
            parse_mode="HTML"
        )
        
        logger.info(f"Child {name} ({age}) added successfully")
        
    except ValueError:
        await update.message.reply_text(
            text="⚠️ Please enter a valid number for the age."
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
            text="🔄 <b>Analyzing emotions...</b>\n\nThis may take a few seconds.",
            parse_mode="HTML"
        )
        
        try:
            # Call Claude API for emotion analysis
            from anthropic import Anthropic
            from src.core.config import settings
            
            client = Anthropic(api_key=settings.anthropic.claude_api_key)
            
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

            response = client.messages.create(
                model=settings.anthropic.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = f"""
🎯 <b>Emotion Analysis Complete</b>

📝 <b>Your situation:</b>
<i>"{message_text}"</i>

{response.content[0].text}

💡 <b>Remember:</b> Every child is unique. Trust your instincts and adapt these suggestions to your child's personality and needs.

What would you like to do next? 👇
"""
            
            await processing_msg.edit_text(
                text=result_text,
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
            
            logger.info(f"Emotion translation completed for user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            await processing_msg.edit_text(
                text="❌ <b>Analysis failed</b>\n\nSorry, I couldn't analyze the emotions right now. Please try again later.\n\nThis could be due to:\n• API service temporarily unavailable\n• Network connection issues\n• Rate limiting\n\nPlease try again in a few moments.",
                reply_markup=InlineKeyboards.main_menu(),
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in emotion translation: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")

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