from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from services.user_manager import UserManager

router = Router()

@router.message(Command("usage"))
async def show_usage(message: Message):
    """Показывает использование API пользователем"""
    user_manager = UserManager()
    
    try:
        # Для бесплатной версии показываем общую информацию
        await message.answer(
            "📊 Вы используете бесплатную версию FinCopilot\n\n"
            "• 🤖 Используется общий API ключ\n"
            "• 💰 Все функции доступны бесплатно\n"
            "• 📈 Ограничения: стандартные лимиты OpenRouter\n\n"
            "💡 Для увеличения лимитов можете получить свой API ключ на openrouter.ai"
        )
            
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {str(e)}")

@router.message(Command("profile"))
async def show_profile(message: Message):
    """Показывает профиль пользователя"""
    user_manager = UserManager()
    
    try:
        user = await user_manager.get_or_create_user(
            message.from_user.id,
            message.from_user.username or "",
            message.from_user.first_name,
            message.from_user.last_name or ""
        )
        
        profile_text = (
            f"👤 Ваш профиль:\n\n"
            f"• ID: {user.user_id}\n"
            f"• Имя: {user.first_name}\n"
            f"• Username: {user.username or 'не указан'}\n"
            f"• Статус: 🆓 Бесплатный\n"
            f"• Зарегистрирован: {user.created_at[:10] if user.created_at else 'неизвестно'}\n"
        )
        
        await message.answer(profile_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения профиля: {str(e)}")

@router.message(Command("status"))
async def show_status(message: Message):
    """Показывает статус системы"""
    await message.answer(
        "🟢 FinCopilot работает в бесплатном режиме\n\n"
        "• 🤖 AI: OpenRouter (бесплатные модели)\n"
        "• 📊 Хранение: Google Sheets\n"
        "• 💰 Стоимость: бесплатно\n\n"
        "Для начала работы просто напишите:\n"
        "• 'расход 2500 на рекламу'\n"
        "• 'доход 15000 за консультацию'"
    )