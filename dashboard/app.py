"""Streamlit дашборд для ML сервиса."""

import json
import os
from io import StringIO

import pandas as pd
import requests
import streamlit as st

# Конфигурация API - сначала проверяем переменную окружения, потом secrets
API_URL = os.getenv("API_URL")
if not API_URL:
    try:
        API_URL = st.secrets.get("API_URL", "http://localhost:8000")
    except:
        API_URL = "http://localhost:8000"


def main():
    """Главная функция дашборда."""
    st.set_page_config(
        page_title="ML Model Training Dashboard",
        page_icon="🤖",
        layout="wide",
    )

    st.title("🤖 ML Model Training Dashboard")
    st.markdown("---")

    # Отладка: показываем какой API_URL используется
    st.sidebar.info(f"🔗 API URL: {API_URL}")

    # Проверка здоровья API
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ API подключен")
        else:
            st.sidebar.error("❌ API недоступен")
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка подключения: {e}")
        API_URL_input = st.sidebar.text_input("URL API", value=API_URL, key="api_url_input")
        if API_URL_input != API_URL:
            st.rerun()

    # Навигация
    page = st.sidebar.radio(
        "Навигация",
        ["📊 Датасеты", "🎓 Обучение моделей", "🔮 Предсказания", "📋 Управление моделями"],
    )

    if page == "📊 Датасеты":
        datasets_page()
    elif page == "🎓 Обучение моделей":
        training_page()
    elif page == "🔮 Предсказания":
        inference_page()
    elif page == "📋 Управление моделями":
        models_management_page()


def datasets_page():
    """Страница управления датасетами."""
    st.header("📊 Управление датасетами")

    tab1, tab2, tab3 = st.tabs(["Просмотр датасетов", "Загрузка датасета", "Информация"])

    with tab1:
        st.subheader("Список датасетов")

        if st.button("🔄 Обновить список"):
            st.rerun()

        try:
            response = requests.get(f"{API_URL}/api/datasets", timeout=10)
            if response.status_code == 200:
                datasets = response.json()

                if datasets:
                    for ds in datasets:
                        with st.expander(f"📄 {ds['name']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Размер", f"{ds['size'] / 1024:.2f} KB")
                            col2.metric("Строк", ds.get("rows", "N/A"))
                            col3.metric("Колонок", len(ds.get("columns", [])))

                            if ds.get("columns"):
                                st.write("**Колонки:**", ", ".join(ds["columns"]))

                            st.write("**Загружен:**", ds["uploaded_at"])

                            if st.button(f"🗑️ Удалить", key=f"delete_{ds['name']}"):
                                delete_response = requests.delete(
                                    f"{API_URL}/api/datasets/{ds['name']}"
                                )
                                if delete_response.status_code == 200:
                                    st.success(f"Датасет {ds['name']} удален")
                                    st.rerun()
                                else:
                                    st.error("Ошибка при удалении")
                else:
                    st.info("Нет загруженных датасетов")
            else:
                st.error(f"Ошибка при получении списка датасетов: {response.status_code}")
        except Exception as e:
            st.error(f"Ошибка подключения: {e}")

    with tab2:
        st.subheader("Загрузка нового датасета")

        uploaded_file = st.file_uploader(
            "Выберите файл (CSV или JSON)",
            type=["csv", "json"],
        )

        if uploaded_file is not None:
            st.write("**Предпросмотр:**")

            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_json(uploaded_file)

                st.dataframe(df.head(10), use_container_width=True)
                st.write(f"Форма данных: {df.shape[0]} строк × {df.shape[1]} колонок")

                if st.button("📤 Загрузить датасет"):
                    uploaded_file.seek(0)
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}

                    response = requests.post(
                        f"{API_URL}/api/datasets/upload",
                        files=files,
                        timeout=30,
                    )

                    if response.status_code == 201:
                        st.success("✅ Датасет успешно загружен!")
                        st.rerun()
                    else:
                        st.error(f"Ошибка при загрузке: {response.text}")

            except Exception as e:
                st.error(f"Ошибка при чтении файла: {e}")

    with tab3:
        st.subheader("Информация о датасете")

        try:
            response = requests.get(f"{API_URL}/api/datasets", timeout=10)
            if response.status_code == 200:
                datasets = response.json()

                if datasets:
                    dataset_names = [ds["name"] for ds in datasets]
                    selected_dataset = st.selectbox("Выберите датасет", dataset_names)

                    if selected_dataset:
                        ds_info = next(ds for ds in datasets if ds["name"] == selected_dataset)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Имя", ds_info["name"])
                            st.metric("Размер", f"{ds_info['size'] / 1024:.2f} KB")
                        with col2:
                            st.metric("Строк", ds_info.get("rows", "N/A"))
                            st.metric("Колонок", len(ds_info.get("columns", [])))

                        if ds_info.get("columns"):
                            st.write("**Список колонок:**")
                            st.write(ds_info["columns"])
                else:
                    st.info("Нет загруженных датасетов")
        except Exception as e:
            st.error(f"Ошибка: {e}")


def training_page():
    """Страница обучения моделей."""
    st.header("🎓 Обучение моделей")

    # Получаем доступные типы моделей
    try:
        response = requests.get(f"{API_URL}/api/models/types", timeout=10)
        if response.status_code == 200:
            model_types = response.json()
        else:
            st.error("Не удалось получить типы моделей")
            return
    except Exception as e:
        st.error(f"Ошибка подключения: {e}")
        return

    # Получаем датасеты
    try:
        response = requests.get(f"{API_URL}/api/datasets", timeout=10)
        if response.status_code == 200:
            datasets = response.json()
            dataset_names = [ds["name"] for ds in datasets]
        else:
            st.error("Не удалось получить список датасетов")
            dataset_names = []
    except Exception as e:
        st.error(f"Ошибка: {e}")
        dataset_names = []

    if not dataset_names:
        st.warning("⚠️ Сначала загрузите датасет на странице 'Датасеты'")
        return

    # Форма обучения
    with st.form("training_form"):
        st.subheader("Параметры обучения")

        col1, col2 = st.columns(2)

        with col1:
            model_name = st.text_input("Имя модели", value="my_model")
            model_type_names = [mt["name"] for mt in model_types]
            selected_model_type = st.selectbox("Тип модели", model_type_names)

        with col2:
            dataset_name = st.selectbox("Датасет", dataset_names)
            target_column = st.text_input("Целевая колонка", value="target")

        # Показываем описание модели
        selected_model_info = next(mt for mt in model_types if mt["name"] == selected_model_type)
        st.info(f"ℹ️ {selected_model_info['description']}")

        # Гиперпараметры
        st.subheader("Гиперпараметры (JSON)")
        default_hyperparams = json.dumps(selected_model_info["hyperparameters"], indent=2)
        hyperparams_text = st.text_area(
            "Гиперпараметры",
            value=default_hyperparams,
            height=200,
        )

        submitted = st.form_submit_button("🚀 Начать обучение")

        if submitted:
            try:
                hyperparams = json.loads(hyperparams_text) if hyperparams_text else None

                payload = {
                    "model_type": selected_model_type,
                    "model_name": model_name,
                    "dataset_name": dataset_name,
                    "target_column": target_column,
                    "hyperparameters": hyperparams,
                }

                with st.spinner("Обучение модели..."):
                    response = requests.post(
                        f"{API_URL}/api/models/train",
                        json=payload,
                        timeout=300,
                    )

                if response.status_code == 201:
                    result = response.json()
                    st.success("✅ Модель успешно обучена!")

                    st.subheader("Метрики модели")
                    metrics = result["metrics"]

                    cols = st.columns(len(metrics))
                    for idx, (metric_name, metric_value) in enumerate(metrics.items()):
                        cols[idx].metric(metric_name.upper(), f"{metric_value:.4f}")

                    st.json(result)
                else:
                    st.error(f"Ошибка при обучении: {response.text}")

            except json.JSONDecodeError:
                st.error("Ошибка в формате JSON гиперпараметров")
            except Exception as e:
                st.error(f"Ошибка: {e}")


def inference_page():
    """Страница предсказаний."""
    st.header("🔮 Предсказания")

    # Получаем список моделей
    try:
        response = requests.get(f"{API_URL}/api/models", timeout=10)
        if response.status_code == 200:
            models = response.json()
        else:
            st.error("Не удалось получить список моделей")
            return
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return

    if not models:
        st.warning("⚠️ Сначала обучите модель на странице 'Обучение моделей'")
        return

    model_names = [m["name"] for m in models]
    selected_model = st.selectbox("Выберите модель", model_names)

    # Информация о модели
    model_info = next(m for m in models if m["name"] == selected_model)

    col1, col2, col3 = st.columns(3)
    col1.metric("Тип модели", model_info["type"])
    col2.metric("Дата создания", model_info["created_at"][:10])

    if model_info.get("metrics"):
        with st.expander("📊 Метрики модели"):
            st.json(model_info["metrics"])

    st.markdown("---")

    # Два способа ввода данных
    input_method = st.radio("Способ ввода данных", ["JSON", "Форма"])

    if input_method == "JSON":
        st.subheader("Ввод данных в формате JSON")

        example_data = [
            {"feature1": 1.0, "feature2": 2.0},
            {"feature1": 3.0, "feature2": 4.0},
        ]

        data_text = st.text_area(
            "Данные для предсказания (список словарей)",
            value=json.dumps(example_data, indent=2),
            height=200,
        )

        if st.button("🔮 Получить предсказания"):
            try:
                data = json.loads(data_text)

                payload = {
                    "model_name": selected_model,
                    "data": data,
                }

                with st.spinner("Получение предсказаний..."):
                    response = requests.post(
                        f"{API_URL}/api/models/predict",
                        json=payload,
                        timeout=30,
                    )

                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Предсказания получены!")

                    # Показываем результаты
                    df = pd.DataFrame(data)
                    df["Предсказание"] = result["predictions"]

                    st.dataframe(df, use_container_width=True)

                    st.download_button(
                        "📥 Скачать результаты (CSV)",
                        df.to_csv(index=False),
                        file_name="predictions.csv",
                        mime="text/csv",
                    )
                else:
                    # Парсим ошибку из API
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", response.text)
                    except:
                        error_detail = response.text

                    # Форматируем ошибку для лучшей читаемости
                    st.error("❌ Ошибка при получении предсказаний")
                    st.error(error_detail)

                    # Дополнительные подсказки для частых ошибок
                    if "feature names" in error_detail.lower() or "feature" in error_detail.lower():
                        st.info(
                            "💡 **Подсказка:** Убедитесь, что названия колонок в данных для предсказания точно совпадают с теми, что использовались при обучении модели."
                        )
                        st.info(
                            "Проверьте информацию о модели выше, чтобы узнать, какие признаки она ожидает."
                        )

            except json.JSONDecodeError:
                st.error("Ошибка в формате JSON")
            except Exception as e:
                st.error(f"Ошибка: {e}")

    else:  # Форма
        st.subheader("Ввод данных через форму")
        st.info("Введите значения признаков. Для добавления строк используйте формат CSV.")

        csv_input = st.text_area(
            "Данные (CSV формат с заголовками)",
            value="feature1,feature2\n1.0,2.0\n3.0,4.0",
            height=150,
        )

        if st.button("🔮 Получить предсказания", key="predict_form"):
            try:
                df = pd.read_csv(StringIO(csv_input))
                data = df.to_dict("records")

                payload = {
                    "model_name": selected_model,
                    "data": data,
                }

                with st.spinner("Получение предсказаний..."):
                    response = requests.post(
                        f"{API_URL}/api/models/predict",
                        json=payload,
                        timeout=30,
                    )

                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Предсказания получены!")

                    df["Предсказание"] = result["predictions"]
                    st.dataframe(df, use_container_width=True)
                else:
                    # Парсим ошибку из API
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", response.text)
                    except:
                        error_detail = response.text

                    # Форматируем ошибку для лучшей читаемости
                    st.error("❌ Ошибка при получении предсказаний")
                    st.error(error_detail)

                    # Дополнительные подсказки для частых ошибок
                    if "feature names" in error_detail.lower() or "feature" in error_detail.lower():
                        st.info(
                            "💡 **Подсказка:** Убедитесь, что названия колонок в CSV точно совпадают с теми, что использовались при обучении модели."
                        )
                        st.info(
                            "Проверьте информацию о модели выше, чтобы узнать, какие признаки она ожидает."
                        )

            except Exception as e:
                st.error(f"Ошибка: {e}")


def models_management_page():
    """Страница управления моделями."""
    st.header("📋 Управление моделями")

    if st.button("🔄 Обновить список"):
        st.rerun()

    try:
        response = requests.get(f"{API_URL}/api/models", timeout=10)
        if response.status_code == 200:
            models = response.json()

            if models:
                for model in models:
                    with st.expander(f"🤖 {model['name']} ({model['type']})"):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.write(f"**Тип:** {model['type']}")
                            st.write(f"**Создана:** {model['created_at']}")

                            if model.get("metrics"):
                                st.write("**Метрики:**")
                                metrics_df = pd.DataFrame([model["metrics"]])
                                st.dataframe(metrics_df, use_container_width=True)

                        with col2:
                            if st.button("🗑️ Удалить", key=f"delete_model_{model['name']}"):
                                delete_response = requests.delete(
                                    f"{API_URL}/api/models/{model['name']}"
                                )
                                if delete_response.status_code == 200:
                                    st.success(f"Модель {model['name']} удалена")
                                    st.rerun()
                                else:
                                    st.error("Ошибка при удалении")
            else:
                st.info("Нет обученных моделей")
        else:
            st.error(f"Ошибка при получении списка моделей: {response.status_code}")
    except Exception as e:
        st.error(f"Ошибка подключения: {e}")


if __name__ == "__main__":
    main()
