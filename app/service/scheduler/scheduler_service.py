import sched
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from app.db.prisma import prisma
from app.utils.datetime_utils import getNow, beforeHours
from app.db.supabase import SupabaseService
from app.service.file.file_service import FileService
from app.const import *


sched = BackgroundScheduler(timezone="Asia/Seoul")


class SchedulerService(object):
    _instance = None
    _tmp_usage_dir = file_output_dir["tmp_usage"]

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    # 매일 새벽 1시 30분에 작동
    # @sched.scheduled_job('cron', hour='1', minute='30', id='remove_inactive_image')

    def start(self):
        sched.start()

    # @sched.scheduled_job("cron", second="*/1")
    # def test():
    #     print("hey")

    # # 1시간마다 uploadDate가 2시간 경과된 파일 삭제
    @sched.scheduled_job("cron", hour="*/1")
    def scheduled_job_every_two_hours():
        print("This job runs every two hours.")

        files = prisma.file.find_many(
            where={
                "uploadDate": {
                    "lte": beforeHours(getNow(), 2),
                },
            },
        )

        prisma.documents.delete_many(
            where={
                "createdAt": {
                    "lte": beforeHours(getNow(), 2),
                }
            }
        )

        tmp_file_path_list = [
            (file.userEmail, file.tmpFilePath, file.filename) for file in files
        ]
        file_path_list = [file.filePath for file in files]
        id_list = [file.id for file in files]
        if len(file_path_list) > 0:
            result = SupabaseService().delete_all_file_on_supabase(
                file_path_list=file_path_list, id_list=id_list
            )

            for info in tmp_file_path_list:
                email, tmp_file_path, filename = info
                if tmp_file_path is None:
                    continue
                FileService().delete_file(tmp_file_path)
                if email is not None:
                    print(f"./.cache/docs/embeddings/{email}/{filename}")
                    FileService().delete_dir_with_contents(
                        f"./.cache/docs/embeddings/{email}/{filename}"
                    )
                    FileService().delete_dir_with_contents(
                        f"./tmp_usage_files/{email}/docs/{filename}"
                    )

            print(f"delete result: {result}")

    # d + 2 < c
    # d < c - 2

    # # 4시간마다
    # @sched.scheduled_job("cron", hour="*/4")
    # def scheduled_job_every_two_hours():
    #     print("This job runs every two hours.")
    #     prisma.file.delete_many(
    #         where={
    #             "uploadDate": {
    #                 "lte": afterHours(getNow(), 4),
    #             },
    #         },
    #     )

    # 24시간마다, 즉 매일 실행되는 작업
    # @sched.scheduled_job("cron", hour=0)
    # def scheduled_job_every_day():
    #     print("This job runs every day at midnight.")
