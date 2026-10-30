"""
EnglishCard - Приложение для изучения английского языка
Базовый файл-заготовка для курсовой работы
Студенту необходимо доработать этот файл в соответствии с заданием
"""

import streamlit as st
import pandas as pd
import random
import psycopg2
import sqlalchemy as sql
from sqlalchemy import case, select, delete
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import insert
from config import DSN
import json
from models import *
from datetime import datetime

# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="EnglishCard - Изучение английского",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# РАБОТА С БАЗОЙ ДАННЫХ (НЕОБХОДИМО РЕАЛИЗОВАТЬ)
# ============================================================
engine = sql.create_engine(DSN, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

SEED_WORDS = [
    ("красный", "red"),
    ("синий", "blue"),
    ("зеленый", "green"),
    ("желтый", "yellow"),
    ("оранжевый", "orange"),
    ("фиолетовый", "purple"),
    ("серый", "gray"),
    ("черный", "black"),
    ("белый", "white"),
    ("розовый", "pink"),
    ("я", "I"),
    ("ты", "you"),
    ("он", "he"),
    ("мы", "we"),
    ("вы", "you (plural)"),
    ("они", "they"),
    ("что", "what"),
    ("как", "how"),
    ("где", "where"),
    ("когда", "when"),
]


def get_db_connection():
    return SessionLocal()


def init_db():
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        existing = {w.russian_word for w in session.query(CommonWord).all()}
        to_add = [
            CommonWord(russian_word=ru, english_word=en)
            for ru, en in SEED_WORDS
            if ru not in existing
        ]
        if to_add:
            session.add_all(to_add)
            session.commit()


def login_user(username):
    session = get_db_connection()
    try:
        stmt = (
            insert(User)
            .values(username=username)
            .on_conflict_do_nothing(index_elements=["username"])
            .returning(User.id)
        )
        user_id = session.execute(stmt).scalar_one_or_none()
        if user_id is None:
            user_id = session.query(User.id).filter_by(username=username).scalar()
        session.commit()
        return user_id
    finally:
        session.close()


def get_user_words(user_id):
    """
    Получить все слова пользователя (общие + персональные): список словарей: [{'id': 1, 'russian_word': 'красный', 'english_word': 'red', 'word_type': 'common'}, ...]
    """
    if user_id is None:
        return []

    session = get_db_connection()
    try:
        word_type = case(
            (UserWord.word_id.is_(None), "personal"),
            else_="common",
        )
        stmt = (
            select(
                UserWord.id,
                UserWord.russian_word,
                UserWord.english_word,
                word_type.label("word_type"),
            )
            .where(UserWord.user_id == user_id)
        )
        rows = session.execute(stmt).all()
        return [
            {
                "id": row.id,
                "russian_word": row.russian_word,
                "english_word": row.english_word,
                "word_type": row.word_type,
            }
            for row in rows
        ]
    finally:
        session.close()


def add_personal_word(user_id, russian_word, english_word):
    """
    TODO: Добавить персональное слово для пользователя
    Проверить, нет ли уже такого слова
    Возвращает True/False
    """
    session = get_db_connection()
    try:
        stmt = (
            insert(UserWord)
            .values(user_id=user_id, word_id=None, russian_word=russian_word, english_word=english_word)
            .on_conflict_do_nothing(index_elements=["user_id", "russian_word", "english_word"])
            .returning(UserWord.id)
        )
        inserted_id = session.execute(stmt).scalar_one_or_none()
        session.commit()
        return inserted_id is not None
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_personal_word(user_id, user_word_id):
    """
    TODO: Удалить персональное слово пользователя
    Возвращает True/False
    """
    session = get_db_connection()
    try:
        stmt = (
            delete(UserWord)
            .where(UserWord.user_id == user_id,
                   UserWord.id == user_word_id,
                   UserWord.word_id.is_(None))
            .returning(UserWord.id)
        )
        deleted_id = session.execute(stmt).scalar_one_or_none()
        session.commit()
        return deleted_id is not None
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_stats(user_id, word_id, word_type, is_correct):
    """
    TODO: Обновить статистику изучения слова
    """
    session = get_db_connection()
    try:
        stmt = (
            insert(LearningStat)
            .values(
                user_id=user_id,
                word_id=word_id,
                word_type=word_type,
                correct_answers=1 if is_correct else 0,
                total_attempts=1,
                last_reviewed=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["user_id", "word_id"],
                set_={
                    "total_attempts": LearningStat.total_attempts + 1,
                    "correct_answers": LearningStat.correct_answers + (1 if is_correct else 0),
                    "last_reviewed": datetime.utcnow(),
                    "word_type": word_type,
                },
            )
            .returning(
                LearningStat.id,
                LearningStat.correct_answers,
                LearningStat.total_attempts,
                LearningStat.last_reviewed,
            )
        )
        row = session.execute(stmt).one()
        session.commit()
        return {
            "id": row.id,
            "correct_answers": row.correct_answers,
            "total_attempts": row.total_attempts,
            "last_reviewed": row.last_reviewed,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_statistics(user_id):
    """
    TODO: Получить статистику пользователя
    Возвращает словарь со статистикой
    """
    session = get_db_connection()
    try:
        stmt = (
            select(
                LearningStat.id,
                LearningStat.user_id,
                LearningStat.word_id,
                LearningStat.word_type,
                LearningStat.correct_answers,
                LearningStat.total_attempts,
                LearningStat.last_reviewed,
                UserWord.russian_word,
                UserWord.english_word,
            )
            .join(UserWord, UserWord.id == LearningStat.word_id)
            .where(LearningStat.user_id == user_id)
        )
        rows = session.execute(stmt).all()
        words = [
            {
                "id": r.id,
                "word_id": r.word_id,
                "word_type": r.word_type,
                "correct_answers": r.correct_answers,
                "total_attempts": r.total_attempts,
                "last_reviewed": r.last_reviewed,
                "russian_word": r.russian_word,
                "english_word": r.english_word,
            }
            for r in rows
        ]

        def _agg(items):
            attempts = sum(i["total_attempts"] for i in items)
            correct = sum(i["correct_answers"] for i in items)
            return {
                "words": len(items),
                "attempts": attempts,
                "correct": correct,
                "accuracy": round(correct / attempts, 3) if attempts else 0.0,
            }

        common_items = [w for w in words if w["word_type"] == "common"]
        personal_items = [w for w in words if w["word_type"] == "personal"]
        total_attempts = sum(w["total_attempts"] for w in words)
        total_correct = sum(w["correct_answers"] for w in words)

        return {
            "user_id": user_id,
            "total_words": len(words),
            "total_attempts": total_attempts,
            "correct_answers": total_correct,
            "accuracy": round(total_correct / total_attempts, 3) if total_attempts else 0.0,
            "by_type": {
                "common": _agg(common_items),
                "personal": _agg(personal_items),
            },
            "words": words,
        }
    finally:
        session.close()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
FALLBACK_WORDS = [
    "apple", "house", "water", "friend", "music",
    "table", "window", "garden", "morning", "yellow",
]

def generate_options(correct_word, all_words):
    """
    TODO: Сгенерировать 4 варианта ответа для викторины
    Один вариант - правильный перевод, остальные - случайные слова из словаря
    Если слов не хватает, можно добавить слова-заглушки
    """
    pool = {w for w in all_words if w and w != correct_word}

    # 2. Берём до 3 случайных неправильных вариантов
    wrong_count = min(3, len(pool))
    wrong_options = random.sample(list(pool), wrong_count) if wrong_count else []

    # 3. Добиваем заглушками, если не хватило
    if len(wrong_options) < 3:
        for fallback in FALLBACK_WORDS:
            if len(wrong_options) >= 3:
                break
            if fallback != correct_word and fallback not in wrong_options:
                wrong_options.append(fallback)

    # 4. Собираем все 4 варианта и перемешиваем
    options = [correct_word] + wrong_options
    random.shuffle(options)
    return options

def ensure_user_common_words(user_id):
    """Добавляет в словарь пользователя общие слова, которых там ещё нет."""
    if user_id is None:
        return

    session = get_db_connection()
    try:
        common_words = session.query(CommonWord).all()

        for word in common_words:
            stmt = (
                insert(UserWord)
                .values(
                    user_id=user_id,
                    word_id=word.id,
                    russian_word=word.russian_word,
                    english_word=word.english_word,
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        "user_id",
                        "russian_word",
                        "english_word",
                    ]
                )
            )
            session.execute(stmt)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
# ============================================================
# ИНТЕРФЕЙС ПРИЛОЖЕНИЯ (НЕОБХОДИМО ДОРАБОТАТЬ)
# ============================================================

def render_sidebar():
    """
    TODO: Реализовать боковую панель с авторизацией
    - Поле для ввода имени
    - Кнопка входа
    - Приветствие после входа
    - Кнопка выхода
    """
    # --- инициализация состояния (внутри функции) ---
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

    with st.sidebar:
        st.header("👤 Авторизация")

        # --- не вошёл ---
        if st.session_state.user_id is None:
            username = st.text_input("Введите имя:", key="login_username_input")

            if st.button("Войти", use_container_width=True):
                username = (username or "").strip()
                if not username:
                    st.warning("Введите имя — оно не может быть пустым.")
                else:
                    try:
                        user_id = login_user(username)
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.success(f"Добро пожаловать, **{username}**!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Не удалось войти: {e}")

        # --- вошёл ---
        else:
            st.success(f"Вы вошли как **{st.session_state.username}**")
            st.caption(f"user_id: {st.session_state.user_id}")

            if st.button("Выйти", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.pop("study", None)
                st.session_state.pop("delete_select", None)
                st.rerun()


def render_study_tab(user_id, words):
    """
    TODO: Реализовать вкладку изучения слов
    - Отображение текущего слова на русском
    - 4 кнопки с вариантами перевода
    - Обработка правильных/неправильных ответов
    - Кнопка следующего слова
    """
    st.subheader("🎯 Изучение слов")

    if user_id is None:
        st.warning("Сначала войдите в систему (боковая панель).")
        return

    # ---------- инициализация состояния ----------
    if "study" not in st.session_state:
        st.session_state.study = {
            "current": None,     # dict текущего слова
            "options": [],       # 4 варианта перевода (строки)
            "answered": None,    # None | "correct" | "wrong"
            "chosen": None,      # какой вариант нажал пользователь
            "score": 0,
            "total": 0,
        }
    state = st.session_state.study

    # ---------- выбор нового слова ----------
    def pick_new_word():
        word = random.choice(words)
        all_translations = [w["english_word"] for w in words]
        state["current"] = word
        state["options"] = generate_options(word["english_word"], all_translations)
        state["answered"] = None
        state["chosen"] = None

    if state["current"] is None:
        pick_new_word()

    word = state["current"]

    # ---------- шапка со счетом за сессию ----------
    col1, col2 = st.columns(2)
    col1.metric("Правильно", state["score"])
    col2.metric("Всего ответов", state["total"])

    st.divider()

    # ---------- текущее слово ----------
    st.markdown("### Переведите слово:")
    st.markdown(f"## 🇷🇺 {word['russian_word']}")
    badge = "🏷️ общее" if word["word_type"] == "common" else "🏷️ личное"
    st.caption(badge)

    # ---------- варианты ответа ----------
    disabled = state["answered"] is not None
    cols = st.columns(2)

    for i, option in enumerate(state["options"]):
        with cols[i % 2]:
            if state["answered"] is not None:
                # после ответа — подсветка вместо кнопок
                if option == word["english_word"]:
                    st.success(f"✅ {option}")
                elif option == state["chosen"]:
                    st.error(f"❌ {option}")
                else:
                    st.button(
                        option,
                        key=f"opt_{i}_{word['id']}_disabled",
                        disabled=True,
                        use_container_width=True,
                    )
            else:
                if st.button(
                        option,
                        key=f"opt_{i}_{word['id']}",
                        use_container_width=True,
                ):
                    state["chosen"] = option
                    state["total"] += 1
                    is_correct = option == word["english_word"]
                    state["answered"] = "correct" if is_correct else "wrong"
                    if is_correct:
                        state["score"] += 1

                    # --- запись статистики в БД ---
                    try:
                        update_stats(
                            user_id=user_id,
                            word_id=word["id"],
                            word_type=word["word_type"],
                            is_correct=is_correct,
                        )
                    except Exception as e:
                        st.error(f"Не удалось сохранить статистику: {e}")

                    st.rerun()

    # ---------- обратная связь ----------
    if state["answered"] == "correct":
        st.success("Правильно! 🎉")
    elif state["answered"] == "wrong":
        st.error(f"Неправильно. Правильный ответ: **{word['english_word']}**")

    # ---------- кнопка «Следующее слово» ----------
    if state["answered"] is not None:
        if st.button("Следующее слово ➡️", type="primary", use_container_width=True):
            pick_new_word()
            st.rerun()

    # ---------- сброс прогресса сессии ----------
    st.divider()
    if st.button("🔄 Сбросить счёт сессии", use_container_width=True):
        state["score"] = 0
        state["total"] = 0
        pick_new_word()
        st.rerun()


def render_add_word_tab(user_id):
    """
    TODO: Реализовать вкладку добавления слова
    - Поле для ввода слова на русском
    - Поле для ввода перевода
    - Кнопка добавления
    - Уведомление об успешном добавлении
    """
    st.subheader("➕ Добавить слово")

    if user_id is None:
        st.warning("Сначала войдите в систему (боковая панель).")
        return

    # ---------- форма ----------
    # clear_on_submit=True очищает поля после успешной отправки
    with st.form("add_word_form", clear_on_submit=True):
        russian_word = st.text_input("Слово на русском", key="add_ru")
        english_word = st.text_input("Перевод на английский", key="add_en")
        submitted = st.form_submit_button("Добавить", use_container_width=True)

    if not submitted:
        return

    # ---------- валидация ----------
    russian_word = (russian_word or "").strip()
    english_word = (english_word or "").strip()

    if not russian_word or not english_word:
        st.warning("Заполните оба поля — слово и перевод не могут быть пустыми.")
        return

    if len(russian_word) > 100 or len(english_word) > 100:
        st.warning("Слишком длинное слово (максимум 100 символов).")
        return

    # ---------- сохранение ----------
    try:
        added = add_personal_word(user_id, russian_word, english_word)
    except Exception as e:
        st.error(f"Не удалось добавить слово: {e}")
        return

    if added:
        st.success(f"Слово **{russian_word} → {english_word}** добавлено ✅")
        st.balloons()
        # сбрасываем состояние «Изучения», чтобы новое слово попало в пул
        st.session_state.pop("study", None)
    else:
        st.info(
            f"Слово **{russian_word} → {english_word}** уже есть в вашем словаре."
        )


def render_delete_word_tab(user_id, words):
    """
    TODO: Реализовать вкладку удаления слова
    - Выпадающий список с персональными словами пользователя
    - Кнопка удаления
    - Подтверждение удаления
    """
    if user_id is None:
        st.warning("Сначала войдите в систему (боковая панель).")
        return

    # ---------- отбираем только персональные слова ----------
    personal_words = [w for w in words if w["word_type"] == "personal"]

    if not personal_words:
        st.info(
            "У вас нет персональных слов для удаления. "
            "Общие слова удалить нельзя — их можно только изучать."
        )
        return

    # ---------- выбор слова ----------
    label_by_id = {
        w["id"]: f"{w['russian_word']} → {w['english_word']}"
        for w in personal_words
    }
    word_ids = [w["id"] for w in personal_words]

    selected_id = st.selectbox(
        "Выберите слово для удаления:",
        options=word_ids,
        format_func=lambda wid: label_by_id[wid],
        key="delete_select",
    )
    selected_word = next(w for w in personal_words if w["id"] == selected_id)

    # ---------- подтверждение ----------
    # отдельный чекбокс, чтобы случайно не удалить одним кликом
    st.write("")
    confirm = st.checkbox(
        f"Я действительно хочу удалить **{selected_word['russian_word']} → "
        f"{selected_word['english_word']}**",
        key=f"delete_confirm_{selected_id}",
    )

    # ---------- кнопка удаления ----------
    if st.button(
            "Удалить слово",
            type="primary",
            disabled=not confirm,
            use_container_width=True,
    ):
        try:
            deleted = delete_personal_word(user_id, selected_id)
        except Exception as e:
            st.error(f"Не удалось удалить слово: {e}")
            return

        if deleted:
            st.success(
                f"Слово **{selected_word['russian_word']} → "
                f"{selected_word['english_word']}** удалено ✅"
            )
            st.toast("Слово удалено", icon="🗑️")

            # сброс состояния «Изучения» — вдруг оно было текущим
            st.session_state.pop("study", None)

            # сброс выбора в selectbox и чекбокса
            st.session_state.pop("delete_select", None)
            st.session_state.pop(f"delete_confirm_{selected_id}", None)

            st.rerun()
        else:
            st.warning(
                "Слово не найдено или является общим — удаление невозможно."
            )


def render_statistics_tab(user_id):
    """
    TODO: Реализовать вкладку статистики (дополнительное требование)
    - Количество изученных слов
    - Количество попыток
    - Процент правильных ответов
    - История последних попыток
    """
    if user_id is None:
        st.warning("Сначала войдите в систему (боковая панель).")
        return

    try:
        stats = get_statistics(user_id)
    except Exception as e:
        st.error(f"Не удалось загрузить статистику: {e}")
        return

    # ---------- пусто ----------
    if not stats["words"]:
        st.info(
            "Пока нет ни одной попытки. "
            "Перейдите на вкладку «Изучение», чтобы начать."
        )
        return

    # ---------- верхние метрики ----------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Изучено слов", stats["total_words"])
    col2.metric("Всего попыток", stats["total_attempts"])
    col3.metric("Правильных", stats["correct_answers"])
    col4.metric("Точность", f"{stats['accuracy'] * 100:.0f}%")

    st.divider()

    # ---------- разбивка по типу слов ----------
    st.markdown("### По типу слов")
    c1, c2 = st.columns(2)

    for col, key, title in (
            (c1, "common", "🏷️ Общие слова"),
            (c2, "personal", "🏷️ Персональные слова"),
    ):
        agg = stats["by_type"][key]
        with col:
            st.markdown(f"**{title}**")
            st.write(f"Слов: **{agg['words']}**")
            st.write(f"Попыток: **{agg['attempts']}**")
            st.write(f"Правильных: **{agg['correct']}**")
            st.write(f"Точность: **{agg['accuracy'] * 100:.0f}%**")
            if agg["attempts"]:
                st.progress(min(agg["accuracy"], 1.0))

    st.divider()

    # ---------- история последних попыток ----------
    st.markdown("### Последние изученные слова")

    # сортируем по last_reviewed, свежие — сверху
    history = sorted(
        stats["words"],
        key=lambda w: w["last_reviewed"] or datetime.min,
        reverse=True,
    )[:10]   # последние 10

    rows = []
    for w in history:
        # если поля russian_word/english_word есть — покажем их,
        # иначе фолбэк на word_id
        ru = w.get("russian_word") or f"word_id={w['word_id']}"
        en = w.get("english_word") or "—"
        acc = (
            w["correct_answers"] / w["total_attempts"] * 100
            if w["total_attempts"] else 0
        )
        rows.append({
            "Слово": f"{ru} → {en}",
            "Тип": "общее" if w["word_type"] == "common" else "личное",
            "Попыток": w["total_attempts"],
            "Правильных": w["correct_answers"],
            "Точность, %": round(acc, 1),
            "Последний раз": (
                w["last_reviewed"].strftime("%Y-%m-%d %H:%M")
                if w["last_reviewed"] else "—"
            ),
        })

    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("Нет данных о попытках.")

    # ---------- самые проблемные слова ----------
    st.divider()
    st.markdown("### Слова, требующие внимания")

    # те, у кого есть хотя бы одна ошибка, отсортированы по числу ошибок
    difficult = [
        w for w in stats["words"]
        if w["total_attempts"] > w["correct_answers"]
    ]
    difficult.sort(
        key=lambda w: (w["total_attempts"] - w["correct_answers"]),
        reverse=True,
    )
    difficult = difficult[:5]

    if not difficult:
        st.success("Отлично! Пока нет слов с ошибками. 🎉")
    else:
        for w in difficult:
            ru = w.get("russian_word") or f"word_id={w['word_id']}"
            en = w.get("english_word") or "—"
            errors = w["total_attempts"] - w["correct_answers"]
            st.write(
                f"⚠️ **{ru} → {en}** — ошибок: {errors} "
                f"из {w['total_attempts']} попыток"
            )


def render_schema():
    """
    TODO: Реализовать отображение схемы базы данных (дополнительное требование)
    """
    pass


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():
    """
    Главная функция приложения.
    1. Инициализация БД
    2. Авторизация пользователя
    3. Отображение вкладок с функционалом
    4. Приветственное сообщение для неавторизованных
    """
    st.title("📚 EnglishCard - Изучай английский с удовольствием!")

    # ---------- 1. Инициализация состояния сессии ----------
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

    # ---------- 2. Инициализация БД (один раз за процесс) ----------
    # Streamlit перезапускает скрипт на каждый клик — init_db() гонять каждый раз
    # накладно (create_all + SELECT всех слов). Кэшируем.
    @st.cache_resource
    def init_db_once():
        init_db()
        Base.metadata.create_all(bind=engine)
        return True
    init_db_once()




    # ---------- 3. Боковая панель с авторизацией ----------
    render_sidebar()

    # ---------- 4. Основной контент ----------
    user_id = st.session_state.user_id

    if user_id is None:
        # --- неавторизован: приветствие ---
        st.markdown(
            """
            ### Добро пожаловать! 👋

            **EnglishCard** помогает учить английские слова с карточками:

            - ➕ **Добавить слово** — свои слова и переводы
            - 🗑️ **Удалить слово** — убрать персональное слово
            - 🎯 **Изучение** — викторина: слово на русском → 4 варианта перевода
            - 📊 **Статистика** — прогресс, точность, проблемные слова

            👈 **Войдите в боковой панели**, чтобы начать.
            """
        )
        return

    # --- авторизован ---
    words = get_user_words(user_id)
    try:
        ensure_user_common_words(user_id)
        words = get_user_words(user_id)
    except Exception as e:
        st.error(f"Не удалось загрузить словарь: {e}")
        return


    tab_add, tab_del, tab_study, tab_stats = st.tabs(
        [
            "➕ Добавить слово",
            "🗑️ Удалить слово",
            "🎯 Изучение",
            "📊 Статистика",
        ]
    )


    with tab_add:
        render_add_word_tab(user_id)

    with tab_del:
        render_delete_word_tab(user_id, words)

    with tab_study:
        render_study_tab(user_id, words)

    with tab_stats:
        render_statistics_tab(user_id)


if __name__ == "__main__":
    main()