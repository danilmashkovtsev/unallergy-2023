import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLineEdit
from PyQt5.QtCore import Qt
import pyodbc

# Строка подключения к базе данных
connection_string = 'DRIVER={SQL Server};SERVER=VEEBERPC;DATABASE=UNAllergy;UID=DanMash;PWD=veeber'

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UnAllergy")
        self.resize(600, 400)  # Установка размеров окна

        # Создание объекта курсора для выполнения SQL-запросов
        self.connection = pyodbc.connect(connection_string)
        self.cursor = self.connection.cursor()

        # Создание виджетов
        self.dishes_list = QListWidget()
        self.allergens_list = QListWidget()
        self.filter_button = QPushButton("Применить фильтр")
        self.reset_button = QPushButton("Сбросить фильтры")
        self.new_allergen_input = QLineEdit()  # Поле ввода нового аллергена
        self.add_allergen_button = QPushButton("Добавить аллерген")

        # Заполнение списка блюд
        self.populate_dishes_list()

        # Заполнение списка аллергенов
        self.populate_allergens_list()

        # Установка обработчика события нажатия кнопки фильтрации
        self.filter_button.clicked.connect(self.filter_dishes)

        # Установка обработчика события нажатия кнопки сброса фильтров
        self.reset_button.clicked.connect(self.reset_filters)

        # Установка обработчика события нажатия кнопки добавления аллергена
        self.add_allergen_button.clicked.connect(self.add_allergen)

        # Создание компоновщика
        layout = QVBoxLayout()
        layout.addWidget(self.dishes_list)
        layout.addWidget(self.allergens_list)
        layout.addWidget(self.filter_button)
        layout.addWidget(self.reset_button)
        layout.addWidget(self.new_allergen_input)
        layout.addWidget(self.add_allergen_button)

        # Установка компоновщика в окне
        self.setLayout(layout)

    def populate_dishes_list(self):
        # Выполнение SQL-запроса для получения списка блюд
        self.cursor.execute('SELECT name_dish FROM Dish')
        results = self.cursor.fetchall()

        # Очистка списка блюд
        self.dishes_list.clear()

        # Добавление блюд в список
        for row in results:
            dish_name = row[0]
            self.dishes_list.addItem(dish_name)

    def populate_allergens_list(self):
        # Выполнение SQL-запроса для получения списка аллергенов
        self.cursor.execute('SELECT name_allergen FROM Allergen')
        results = self.cursor.fetchall()

        # Очистка списка аллергенов
        self.allergens_list.clear()

        # Добавление аллергенов в список с возможностью выбора
        for row in results:
            allergen_name = row[0]
            item = QListWidgetItem(allergen_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.allergens_list.addItem(item)

    def filter_dishes(self):
        try:
            selected_allergens = []

            # Получение выбранных аллергенов
            for index in range(self.allergens_list.count()):
                item = self.allergens_list.item(index)
                if item.checkState() == Qt.Checked:
                    selected_allergens.append(item.text())

            if len(selected_allergens) > 0:
                # Формирование строки с именами выбранных аллергенов для использования в SQL-запросе
                allergen_names = "'" + "','".join(selected_allergens) + "'"

                # Получение списка ингредиентов, связанных с выбранными аллергенами
                ingredient_query = f"""
                SELECT i.id
                FROM Ingredient i
                JOIN Allergen_Ingredient ai ON i.id = ai.id_ingredient
                JOIN Allergen a ON ai.id_allergen = a.id
                WHERE a.name_allergen IN ({allergen_names})
                """
                self.cursor.execute(ingredient_query)
                ingredient_ids = [row[0] for row in self.cursor.fetchall()]

                if len(ingredient_ids) > 0:
                    # Получение списка блюд, содержащих выбранные ингредиенты
                    dish_query = f"""
                    SELECT DISTINCT d.name_dish
                    FROM Dish d
                    JOIN ConDish c ON d.id = c.id_dish
                    WHERE c.id_ingredient IN ({",".join(str(id) for id in ingredient_ids)})
                    """
                    self.cursor.execute(dish_query)
                    included_dishes = [row[0] for row in self.cursor.fetchall()]

                    # Выполняем запрос на получение всех блюд, кроме исключенных
                    query = "SELECT name_dish FROM Dish WHERE name_dish IN ({})".format(
                        ",".join(["?"] * len(included_dishes))
                    )
                    self.cursor.execute(query, tuple(included_dishes))
                    results = self.cursor.fetchall()

                    # Очистка списка блюд
                    self.dishes_list.clear()

                    # Добавление блюд в список
                    for row in results:
                        dish_name = row[0]
                        self.dishes_list.addItem(dish_name)
                else:
                    # Если нет выбранных ингредиентов, очищаем список блюд
                    self.dishes_list.clear()
            else:
                # Если нет выбранных аллергенов, отображаем все блюда
                self.populate_dishes_list()

        except Exception as e:
            # Вывод сообщения об ошибке
            print("Произошла ошибка при фильтрации блюд:", str(e))

    def add_allergen(self):
        new_allergen = self.new_allergen_input.text().strip()

        if new_allergen:
            # Получение максимального ID аллергена
            self.cursor.execute('SELECT MAX(id_allergen) FROM Allergens')
            max_id = self.cursor.fetchone()[0]
            new_id = max_id + 1

            # Выполнение SQL-запроса для добавления нового аллергена
            query = "INSERT INTO Allergens (id_allergen, name_allergen) VALUES (?, ?)"
            self.cursor.execute(query, new_id, new_allergen)
            self.connection.commit()

            # Обновление списка аллергенов
            self.populate_allergens_list()

            # Применение фильтра заново
            self.filter_dishes()

        # Очистка поля ввода
        self.new_allergen_input.clear()

    def reset_filters(self):
        # Сброс выбранных аллергенов и восстановление полного списка блюд
        self.populate_dishes_list()
        for index in range(self.allergens_list.count()):
            item = self.allergens_list.item(index)
            item.setCheckState(Qt.Unchecked)

    def closeEvent(self, event):
        # Закрытие соединения с базой данных при закрытии окна
        self.cursor.close()
        self.connection.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
