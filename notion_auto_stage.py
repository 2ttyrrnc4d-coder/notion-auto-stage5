import os
import time
from notion_client import Client

class NotionStageAutomation:
    def __init__(self):
        # Получаем токен из переменных окружения GitHub
        notion_token = os.environ.get('NOTION_TOKEN')
        
        if not notion_token:
            raise Exception("NOTION_TOKEN not found in environment variables")
        
        print(f"🔑 Token found: {notion_token[:10]}...")
        
        self.notion = Client(auth=notion_token)
        self.projects_db = "2334aa74d3bd81dd8e87d07e18195649"
        self.stages_db = "2344aa74d3bd80958c46cd097c3f1559"
        self.tasks_db = "2334aa74d3bd81589439ed4116e01fbb"
        
    def get_project_stages(self, project_id):
        """Получить все этапы проекта в правильном порядке"""
        try:
            stages = self.notion.databases.query(
                database_id=self.stages_db,
                filter={
                    "property": "Проект",
                    "relation": {"contains": project_id}
                },
                sorts=[{"property": "Порядок", "direction": "ascending"}]
            )
            return stages.get("results", [])
        except Exception as e:
            print(f"❌ Error getting project stages: {str(e)}")
            return []
    
    def get_stage_tasks(self, stage_id):
        """Получить все задачи этапа"""
        try:
            tasks = self.notion.databases.query(
                database_id=self.tasks_db,
                filter={
                    "property": "Этап", 
                    "relation": {"contains": stage_id}
                }
            )
            return tasks.get("results", [])
        except Exception as e:
            print(f"❌ Error getting stage tasks: {str(e)}")
            return []
    
    def is_stage_completed(self, stage_id):
        """Проверить, все ли задачи этапа выполнены"""
        tasks = self.get_stage_tasks(stage_id)
        if not tasks:
            return False
            
        completed_tasks = [task for task in tasks 
                          if task['properties']['Выполнена']['checkbox']]
        return len(completed_tasks) == len(tasks)
    
    def get_current_stage(self, project):
        """Получить текущий активный этап проекта"""
        try:
            # Пробуем разные возможные названия свойства
            stage_relation = None
            
            if 'Текущий этап' in project['properties']:
                stage_relation = project['properties']['Текущий этап']['relation']
            elif 'Current stage' in project['properties']:
                stage_relation = project['properties']['Current stage']['relation']
            elif 'Stage' in project['properties']:
                stage_relation = project['properties']['Stage']['relation']
            
            return stage_relation[0]['id'] if stage_relation and len(stage_relation) > 0 else None
        except Exception as e:
            print(f"   ⚠️ Ошибка получения текущего этапа: {str(e)}")
            return None
    
    def advance_project_stage(self, project_id, current_stage_id, all_stages):
        """Перевести проект на следующий этап на основе порядка"""
        try:
            current_index = None
            for i, stage in enumerate(all_stages):
                if stage['id'] == current_stage_id:
                    current_index = i
                    break
            
            if current_index is None or current_index + 1 >= len(all_stages):
                print("   ⏹️ Нет следующего этапа для перехода")
                return False
            
            next_stage = all_stages[current_index + 1]
            
            # Безопасное получение названий этапов
            try:
                current_stage_name = all_stages[current_index]['properties']['Name']['title'][0]['text']['content']
            except:
                current_stage_name = f"Этап {current_index + 1}"
            
            try:
                next_stage_name = next_stage['properties']['Название']['title'][0]['text']['content']
            except:
                next_stage_name = f"Этап {current_index + 2}"
            
            print(f"   🔄 Переход с '{current_stage_name}' на '{next_stage_name}'")
            
            # Обновляем проект
            self.notion.pages.update(
                page_id=project_id,
                properties={
                    'Текущий этап': {
                        'relation': [{'id': next_stage['id']}]
                    }
                }
            )
            
            # Обновляем статусы этапов
            self.notion.pages.update(
                page_id=current_stage_id,
                properties={'Статус': {'select': {'name': 'Завершен'}}}
            )
            
            self.notion.pages.update(
                page_id=next_stage['id'],
                properties={'Статус': {'select': {'name': 'Активен'}}}
            )
            
            print(f"   ✅ Успешно переведен на этап: '{next_stage_name}'")
            return True
            
        except Exception as e:
            print(f"   ❌ Ошибка при переходе этапа: {str(e)}")
            return False
    
    def check_all_projects(self):
        """Проверить все проекты и обновить этапы"""
        print(f"🔍 Проверка проектов... {time.strftime('%H:%M:%S')}")
        
        try:
            projects = self.notion.databases.query(
                database_id=self.projects_db
            ).get("results", [])
            
            print(f"📁 Найдено проектов: {len(projects)}")
            
            for project in projects:
                try:
                    # Безопасное получение названия проекта
                    try:
                        project_name = project['properties']['Name']['title'][0]['text']['content']
                    except (KeyError, IndexError, TypeError):
                        project_name = f"Project_{project['id'][-8:]}"
                    
                    print(f"🔍 Проверяю проект: {project_name}")
                    
                    current_stage_id = self.get_current_stage(project)
                    
                    if not current_stage_id:
                        print(f"   ⏭️ Нет текущего этапа")
                        continue
                    
                    # Получаем все этапы проекта
                    all_stages = self.get_project_stages(project['id'])
                    print(f"   📋 Всего этапов: {len(all_stages)}")
                    
                    # Находим текущий этап и его порядковый номер
                    current_stage_index = None
                    current_stage_name = "Неизвестно"
                    for i, stage in enumerate(all_stages):
                        if stage['id'] == current_stage_id:
                            current_stage_index = i + 1  # +1 чтобы считать с 1, а не с 0
                            try:
                                current_stage_name = stage['properties']['Name']['title'][0]['text']['content']
                            except:
                                current_stage_name = f"Этап {current_stage_index}"
                            break
                    
                    print(f"   🎯 Текущий этап: {current_stage_index}/{len(all_stages)} - {current_stage_name}")
                    
                    # Считаем ОБЩИЙ прогресс по всем этапам
                    total_tasks_all_stages = 0
                    completed_tasks_all_stages = 0
                    
                    for stage in all_stages:
                        tasks = self.get_stage_tasks(stage['id'])
                        completed = sum(1 for task in tasks if task['properties']['Выполнена']['checkbox'])
                        total_tasks_all_stages += len(tasks)
                        completed_tasks_all_stages += completed
                    
                    # Считаем прогресс ТЕКУЩЕГО этапа
                    current_tasks = self.get_stage_tasks(current_stage_id)
                    current_completed = sum(1 for task in current_tasks if task['properties']['Выполнена']['checkbox'])
                    current_total = len(current_tasks)
                    
                    print(f"   📊 Прогресс текущего этапа: {current_completed}/{current_total} задач")
                    print(f"   📈 Общий прогресс проекта: {completed_tasks_all_stages}/{total_tasks_all_stages} задач")
                    
                    # Проверяем завершенность текущего этапа
                    if self.is_stage_completed(current_stage_id):
                        print(f"   ✅ Этап завершен - выполняю переход")
                        success = self.advance_project_stage(project['id'], current_stage_id, all_stages)
                        if success:
                            print(f"   🔄 Успешно переключил этап")
                        else:
                            print(f"   ⏹️ Нет следующего этапа для перехода")
                    else:
                        print(f"   ⏳ Этап еще не завершен")
                            
                except Exception as e:
                    print(f"❌ Ошибка в проекте {project.get('id', 'unknown')}: {str(e)}")
        
        except Exception as e:
            print(f"💥 Критическая ошибка при запросе проектов: {str(e)}")
    
    def run_once(self):
        """Запустить одну проверку"""
        print("🚀 Запуск авто-менеджера этапов")
        self.check_all_projects()
        print("✅ Проверка завершена")

if __name__ == "__main__":
    try:
        automation = NotionStageAutomation()
        automation.run_once()
    except Exception as e:
        print(f"💥 Critical error: {str(e)}")
        exit(1)
