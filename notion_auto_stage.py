import os
import time
import schedule
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

class NotionStageAutomation:
    def __init__(self):
        # ✅ ПРАВИЛЬНО: получаем токен из переменных окружения
        notion_token = os.environ.get('NOTION_TOKEN')
        
        if not notion_token:
            raise Exception("NOTION_TOKEN not found in environment variables")
        
        print(f"🔑 Token found: {notion_token[:10]}...")
        
        self.notion = Client(auth=notion_token)  # ← ИСПРАВЛЕНО!
        self.projects_db = "2334aa74d3bd81dd8e87d07e18195649"
        self.stages_db = "2344aa74d3bd80958c46cd097c3f1559"
        self.tasks_db = "2334aa74d3bd81589439ed4116e01fbb"
        
    def get_project_stages(self, project_id):
        """Получить все этапы проекта в правильном порядке"""
        stages = self.notion.databases.query(
            database_id=self.stages_db,
            filter={
                "property": "Проект",
                "relation": {"contains": project_id}
            },
            sorts=[{"property": "Порядок", "direction": "ascending"}]
        )
        return stages.get("results", [])
    
    def get_stage_tasks(self, stage_id):
        """Получить все задачи этапа"""
        tasks = self.notion.databases.query(
            database_id=self.tasks_db,
            filter={
                "property": "Этап", 
                "relation": {"contains": stage_id}
            }
        )
        return tasks.get("results", [])
    
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
        stage_relation = project['properties']['Текущий этап']['relation']
        return stage_relation[0]['id'] if stage_relation else None
    
    def advance_project_stage(self, project_id, current_stage_id, all_stages):
        """Перевести проект на следующий этап"""
        current_index = None
        for i, stage in enumerate(all_stages):
            if stage['id'] == current_stage_id:
                current_index = i
                break
        
        if current_index is None or current_index + 1 >= len(all_stages):
            return False  # Нет следующего этапа
        
        next_stage = all_stages[current_index + 1]
        
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
        
        print(f"✅ Проект переведен на этап: {next_stage['properties']['Название']['title'][0]['text']['content']}")
        return True
    
    def check_all_projects(self):
        """Проверить все проекты и обновить этапы"""
        print(f"🔍 Проверка проектов... {time.strftime('%H:%M:%S')}")
        
        projects = self.notion.databases.query(
            database_id=self.projects_db
        ).get("results", [])
        
        for project in projects:
            try:
                project_name = project['properties']['Название']['title'][0]['text']['content']
                current_stage_id = self.get_current_stage(project)
                
                if not current_stage_id:
                    continue
                
                # Получаем все этапы проекта
                all_stages = self.get_project_stages(project['id'])
                
                # Проверяем завершенность текущего этапа
                if self.is_stage_completed(current_stage_id):
                    print(f"🔄 Проект '{project_name}': текущий этап завершен")
                    self.advance_project_stage(project['id'], current_stage_id, all_stages)
                else:
                    # Считаем прогресс для логов
                    tasks = self.get_stage_tasks(current_stage_id)
                    completed = sum(1 for task in tasks 
                                  if task['properties']['Выполнена']['checkbox'])
                    total = len(tasks)
                    print(f"📊 Проект '{project_name}': прогресс {completed}/{total}")
                        
            except Exception as e:
                print(f"❌ Ошибка в проекте {project.get('id', 'unknown')}: {str(e)}")
    
    def run_once(self):
        """Запустить одну проверку"""
        print("🚀 Запуск авто-менеджера этапов")
        self.check_all_projects()
        print("✅ Проверка завершена")

if __name__ == "__main__":
    automation = NotionStageAutomation()
    automation.run_once()
