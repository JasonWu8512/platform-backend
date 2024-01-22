# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta

class CasenameError(Exception):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return "未定义的打卡case名称: '{}'".format(self.name)

class ParaError(Exception):
    def __init__(self, task, days):
        self.task = task
        self.days = days
    def __str__(self):
        return "参数设置错误，打卡天数{}超出挑战{}限制天数(或小于0)".format(self.days, self.task)

class checkcase:

    day_cfg = {
        'i1': 8,
        'i2': 16,
        'i3': 45,
        'i4': 85,
        'i5': 150,
        'i6': 150
    }

    @classmethod
    def getCase(cls, task, days):
        """ Get checkin case by task and days
        """
        return cls().__getCaseBy(task, days)

    def __getCaseBy(self, task, days):
        self.__checkParameter(task, days)
        isSuccess = (self.day_cfg[task] == days)
        dt = self.__today()
        case = None
        if task == 'i1':
            if isSuccess:
                case = self.__case_i1_success(dt)
            else:
                case = self.__case_i1_ongoing(dt, days)
        elif task == 'i2':
            if isSuccess:
                case = self.__case_i2_success(dt)
            else:
                case = self.__case_i2_ongoing(dt, days)
        elif task == 'i3':
            if isSuccess:
                case = self.__case_i3_success(dt)
            else:
                case = self.__case_i3_ongoing(dt, days)
        elif task == 'i4':
            if isSuccess:
                case = self.__case_i4_success(dt)
            else:
                case = self.__case_i4_ongoing(dt, days)
        elif task == 'i5':
            if isSuccess:
                case = self.__case_i5_success(dt)
            else:
                case = self.__case_i5_ongoing(dt, days)
        elif task == 'i6':
            if isSuccess:
                case = self.__case_i6_success(dt)
            else:
                case = self.__case_i6_ongoing(dt, days)
        else:
            case = None
        return case

    def __today(self):
        return datetime.utcnow()

    def __nDaysAgo(self, dt, n):
        return dt - timedelta(days=n)

    def __nLastDays(self, dt, n):
        result = []
        for i in range(n, 0, -1):
            result.append(dt - timedelta(days=i))
        return result

    def __nDaysFromX(self, dt, x, n):
        """ From x days ago, add n days
        """
        return self.__nLastDays(self.__nDaysAgo(dt, x - n), n)

    def __checkParameter(self, task, days):
        if not task in ('i1', 'i2', 'i3', 'i4', 'i5', 'i6'):
            raise ParaError(task, days)
        if days > self.day_cfg[task] or days < 0:
            raise ParaError(task, days)

    def __case_i1_ongoing(self, dt, n):
        return {
            "current": "i1",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 1,
                "all": 1
            },
            "i1": {
                "id": "i1",
                "state": "checked",
                "start": self.__nDaysAgo(dt, n),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, n)
            },
            "i2": {
                "id": "i2",
                "state": "unjoin"
            },
            "i3": {
                "id": "i3",
                "state": "unjoin"
            },
            "i4": {
                "id": "i4",
                "state": "unjoin"
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            }
        }

    def __case_i1_success(self, dt):
        return {
            "current": "i1",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 8,
                "all": 8,
                "check-history": {
                    "i1": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "success",
                "start": self.__nDaysAgo(dt, 8),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, 8),
                "oid": "P_award_i1_R",
                "chSuccessInfo": {
                    "spuId": 5094,
                    "sguId": 5092,
                    "successTime": self.__nDaysAgo(dt, 1)
                }
            },
            "i2": {
                "id": "i2",
                "state": "unjoin"
            },
            "i3": {
                "id": "i3",
                "state": "unjoin"
            },
            "i4": {
                "id": "i4",
                "state": "unjoin"
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            }
        }

    def __case_i2_ongoing(self, dt, n):
        return {
            "current": "i2",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15 if (n + 8) > 15 else (n + 8),
                "all":  n + 8,
                "check-history": {
                    "i1": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "checked",
                "start": self.__nDaysAgo(dt, n),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, n)
            },
            "i3": {
                "id": "i3",
                "state": "unjoin"
            },
            "i4": {
                "id": "i4",
                "state": "unjoin"
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i1",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, n + 8),
                "calendar": self.__nDaysFromX(dt, n + 8, 8)
            }
        }

    def __case_i2_success(self, dt):
        return {
            "current": "i2",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  8 + 16,
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "success",
                "start": self.__nDaysAgo(dt, 16),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, 16),
                "oid": "P_award_i2_R",
                "chSuccessInfo": {
                    "spuId": 5098,
                    "sguId": 5095,
                    "successTime": self.__nDaysAgo(dt, 1)
                }
            },
            "i3": {
                "id": "i3",
                "state": "unjoin"
            },
            "i4": {
                "id": "i4",
                "state": "unjoin"
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i1",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, 24),
                "calendar": self.__nDaysFromX(dt, 24, 8)
            }
        }

    def __case_i3_ongoing(self, dt, n):
        return {
            "current": "i3",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  n + 8 + 16,
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "checked",
                "start": self.__nDaysAgo(dt, n),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, n)
            },
            "i4": {
                "id": "i4",
                "state": "unjoin"
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i2",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, n + 16),
                "calendar": self.__nDaysFromX(dt, n + 16, 16)
            }
        }

    def __case_i3_success(self, dt):
        return {
            "current": "i3",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  self.day_cfg['i1'] + self.day_cfg['i2'] + self.day_cfg['i3'],
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    },
                    "i3": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "success",
                "start": self.__nDaysAgo(dt, self.day_cfg['i3']),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, self.day_cfg['i3']),
                "oid": "P_award_i3_R",
                "chSuccessInfo": {
                    "spuId": 5099,
                    "sguId": 5097,
                    "successTime": self.__nDaysAgo(dt, 1)
                }
            },
            "i4": {
                "id": "i4",
                "state": "unjoin"
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i2",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, self.day_cfg['i2'] + self.day_cfg['i3']),
                "calendar": self.__nDaysFromX(dt, self.day_cfg['i2'] + self.day_cfg['i3'], self.day_cfg['i2'])
            }
        }

    def __case_i4_ongoing(self, dt, n):
        return {
            "current": "i4",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  n + 8 + 16 + 45,
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    },
                    "i3": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "awarded"
            },
            "i4": {
                "id": "i4",
                "state": "checked",
                "start": self.__nDaysAgo(dt, n),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, n)
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i3",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, n + 45),
                "calendar": self.__nDaysFromX(dt, n + 45, 45)
            }
        }

    def __case_i4_success(self, dt):
        return {
            "current": "i4",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  self.day_cfg['i1'] + self.day_cfg['i2'] + self.day_cfg['i3'] + self.day_cfg['i4'],
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    },
                    "i3": {
                        "success": 1
                    },
                    "i4": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "awarded"
            },
            "i4": {
                "id": "i4",
                "state": "success",
                "start": self.__nDaysAgo(dt, self.day_cfg['i4']),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, self.day_cfg['i4']),
                "oid": "P_award_i4_R",
                "chSuccessInfo": {
                    "spuId": 5102,
                    "sguId": 5101,
                    "successTime": self.__nDaysAgo(dt, 1)
                }
            },
            "i5": {
                "id": "i5",
                "state": "unjoin"
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i3",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, self.day_cfg['i3'] + self.day_cfg['i4']),
                "calendar": self.__nDaysFromX(dt, self.day_cfg['i3'] + self.day_cfg['i4'], self.day_cfg['i3'])
            }
        }

    def __case_i5_ongoing(self, dt, n):
        return {
            "current": "i5",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  n + 8 + 16 + 45 + 85,
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    },
                    "i3": {
                        "success": 1
                    },
                    "i4": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "awarded"
            },
            "i4": {
                "id": "i4",
                "state": "awarded"
            },
            "i5": {
                "id": "i5",
                "state": "checked",
                "start": self.__nDaysAgo(dt, n),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, n)
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i4",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, n + 85),
                "calendar": self.__nDaysFromX(dt, n + 85, 85)
            }
        }

    def __case_i5_success(self, dt):
        return {
            "current": "i5",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  self.day_cfg['i1'] + self.day_cfg['i2'] + self.day_cfg['i3'] + self.day_cfg['i4'] + self.day_cfg['i5'],
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    },
                    "i3": {
                        "success": 1
                    },
                    "i4": {
                        "success": 1
                    },
                    "i5": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "awarded"
            },
            "i4": {
                "id": "i4",
                "state": "awarded"
            },
            "i5": {
                "id": "i5",
                "state": "success",
                "start": self.__nDaysAgo(dt, self.day_cfg['i5']),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, self.day_cfg['i5']),
                "oid": "P_award_i5_R",
                "chSuccessInfo": {
                    "spuId": 5106,
                    "sguId": 5103,
                    "successTime": self.__nDaysAgo(dt, 1)
                }
            },
            "i6": {
                "id": "i6",
                "state": "unjoin"
            },
            "last-challenge": {
                "id": "i4",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, self.day_cfg['i4'] + self.day_cfg['i5']),
                "calendar": self.__nDaysFromX(dt, self.day_cfg['i4'] + self.day_cfg['i5'], self.day_cfg['i4'])
            }
        }

    def __case_i6_ongoing(self, dt, n):
        return {
            "current": "i6",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  n + 8 + 16 + 45 + 85 + 150,
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    },
                    "i3": {
                        "success": 1
                    },
                    "i4": {
                        "success": 1
                    },
                    "i5": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "awarded"
            },
            "i4": {
                "id": "i4",
                "state": "awarded"
            },
            "i5": {
                "id": "i5",
                "state": "awarded"
            },
            "i6": {
                "id": "i6",
                "state": "checked",
                "start": self.__nDaysAgo(dt, n),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, n)
            },
            "last-challenge": {
                "id": "i5",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, n + 150),
                "calendar": self.__nDaysFromX(dt, n + 150, 150)
            }
        }

    def __case_i6_success(self, dt):
        return {
            "current": "i6",
            "rec": {
                "lastchecked": self.__nDaysAgo(dt, 1),
                "15days": 15,
                "all":  self.day_cfg['i1'] + self.day_cfg['i2'] + self.day_cfg['i3'] + self.day_cfg['i4'] + self.day_cfg['i5'] + self.day_cfg['i6'],
                "check-history": {
                    "i1": {
                        "success": 1
                    },
                    "i2": {
                        "success": 1
                    },
                    "i3": {
                        "success": 1
                    },
                    "i4": {
                        "success": 1
                    },
                    "i5": {
                        "success": 1
                    },
                    "i6": {
                        "success": 1
                    }
                }
            },
            "i1": {
                "id": "i1",
                "state": "awarded"
            },
            "i2": {
                "id": "i2",
                "state": "awarded"
            },
            "i3": {
                "id": "i3",
                "state": "awarded"
            },
            "i4": {
                "id": "i4",
                "state": "awarded"
            },
            "i5": {
                "id": "i5",
                "state": "awarded"
            },
            "i6": {
                "id": "i6",
                "state": "success",
                "start": self.__nDaysAgo(dt, self.day_cfg['i6']),
                "lastupdated": self.__nDaysAgo(dt, 1),
                "calendar": self.__nLastDays(dt, self.day_cfg['i6']),
                "oid": "P_award_i6_R",
                "chSuccessInfo": {
                    "spuId": 5108,
                    "sguId": 5107,
                    "successTime": self.__nDaysAgo(dt, 1)
                }
            },
            "last-challenge": {
                "id": "i5",
                "state": "awarded",
                "start": self.__nDaysAgo(dt, self.day_cfg['i5'] + self.day_cfg['i6']),
                "calendar": self.__nDaysFromX(dt, self.day_cfg['i5'] + self.day_cfg['i6'], self.day_cfg['i5'])
            }
        }

