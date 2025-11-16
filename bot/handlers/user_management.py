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
        usage = await user_manager.get_user_usage(message.from_user.id)
        
        if "error" in usage:
            await message.answer("📊 Вы используете общий API ключ. Индивидуальная статистика недоступна.")
        else:
            await message.answer(
                f"📊 Ваша статистика использования:\n\n"
                f"• Использовано в этом месяце: ${usage.get('usage_monthly', 0):.4f}\n"
                f"• Осталось кредитов: ${usage.get('limit_remaining', 0):.2f}\n"
                f"• Лимит: ${usage.get('limit', 0):.2f}\n"
                f"• Использовано сегодня: ${usage.get('usage_daily', 0):.4f}\n\n"
                f"💡 Для увеличения лимита обратитесь к администратору."
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
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        
        profile_text = (
            f"👤 Ваш профиль:\n\n"
            f"• ID: {user.user_id}\n"
            f"• Имя: {user.first_name}\n"
            f"• Username: {user.username or 'не указан'}\n"
            f"• Статус: {'💎 Премиум' if user.is_premium else '🔓 Базовый'}\n"
            f"• Лимит кредитов: ${user.credit_limit:.2f}\n"
            f"• Зарегистрирован: {user.created_at[:10] if user.created_at else 'неизвестно'}\n"
        )
        
        await message.answer(profile_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения профиля: {str(e)}")