# -*- coding: UTF-8 -*-

import pymongo
import os
import getopt
import sys
from pprint import pprint
from zero.dataTool.checkcase  import checkcase, CasenameError, ParaError


class EnvError(Exception):
    def __init__(self, env):
        self.env = env

    def __str__(self):
        return "环境参数设置错误, 不支持: {}".format(self.env)


class TaskError(Exception):
    def __init__(self, task):
        self.task = task

    def __str__(self):
        return "任务设置错误, 不支持: Task{}".format(self.task)


def usage():
    print(
        """
    使用方法:
        python3 set-checkin-state.py [options] <呱号>
    将所提供呱号的账号打卡状态设置为指定状态(今日未打卡)
    
    选项:
        -h, --help                      显示帮助
        -e, --env                       设置脚本执行环境, 默认dev, 可选prod/dev
        -t TASK,
        --task=TASK                     指定任务: 1~6
        -d DAYS,
        --days=DAYS                     指定打卡天数
        
    示例:
        python3 set-checkin-state.py -t 1 -d 1 <呱号>
            设置为挑战1-已打卡1天
        python3 set-checkin-state.py -t 3 -d 10 <呱号>
            设置为挑战3-已打卡10天
        python3 set-checkin-state.py -e prod -t 4 -d 2 <呱号>
            Prod下设置为挑战4-已打卡2天
    """)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:], "he:t:d:", [
                                   "help" "env=" "task=" "days="])
        env = 'dev'
        task = None
        days = None
        for o, a in opts:
            if o in ("-h", "--help"):
                usage()
                return 0
            elif o in ("-e", "--env"):
                if a in ('dev', 'fat', 'prod'):
                    env = a
                else:
                    raise EnvError(a)
            elif o in ("-t", "--task"):
                if a in ('0', '1', '2', '3', '4', '5', '6'):
                    task = 'i' + a
                else:
                    raise TaskError(a)
            elif o in ("-d", "--day"):
                days = int(a)
            else:
                assert False, "unhandled option"
        assert len(args) == 1, "需要提供呱号"
        assert task != None and days != None
        guaid = args[0]

        # Connect to db
        mongo = mongoOpts[env]
        client = pymongo.MongoClient(
            host=mongo['host'], port=mongo['port'], username=mongo["user"],
            password=mongo["pass"], authSource=mongo["authsrc"], authMechanism=mongo["auth"])
        db = client.get_database(mongo['db'])
        user = db.get_collection('users').find_one({'guaid': guaid})
        assert user != None, "提供的呱号不正确"
        uid = user['_id']

        print("guaid: {}, uid: {}".format(guaid, uid))

        # Get case
        if task == 'i0':
            # reset
            db.get_collection('check').delete_one({'_id': uid})
            print("RESET")
        else:
            case = checkcase.getCase(task, days)
            db.get_collection('check').delete_one({'_id': uid})
            db.get_collection('check').update_one(
                {'_id': uid}, {'$set': case}, upsert=True)
            print("SET case, Task: {}, days: {}".format(task, days))

        return 0
    except getopt.GetoptError as err:
        print(err)
        print("要查看使用方法, 请使用 -h 或 --help 参数")
        return 2
    except (AssertionError, CasenameError, EnvError, TaskError, ParaError) as err:
        print(err)
        return 3
    except pymongo.errors.ServerSelectionTimeoutError as err:
        print(err)
        return 4
    except Exception as err:
        print(err)
        return 5

if __name__ == "__main__":
    main()
