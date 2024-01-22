# coding=utf-8
# @Time    : 2020/12/14 11:33 上午
# @Author  : jerry
# @File    : businessEnums.py

from zero.utils.enums.jlgl_enum import *
from zero.lesson_central.models import RPCUri


class GeneralOperationEnum(ChineseEnum):
    delete_user_purchase_record = ChineseTuple(('清除用户购买记录', 'delete_user_purchase_record'))
    top_up_user_guadou_balance = ChineseTuple(('充值10000呱豆', 'top_up_user_guadou_balance'))
    update_users = ChineseTuple(('修改用户信息', 'update_users'))
    get_sms_code = ChineseTuple(('获取短信验证码', 'get_sms_code'))
    create_eshop_order = ChineseTuple(('生成正价课订单', 'create_eshop_order'))
    clean_user_device = ChineseTuple(('清理用户设备', 'clean_user_device'))


class PromoterOperationEnum(ChineseEnum):
    create_Sample_order = ChineseTuple(('购买9.9体验课', 'create_Sample_order'))
    delete_promoter = ChineseTuple(('删除推广人信息', 'delete_promoter'))
    delelte_promoter_wechat = ChineseTuple(('删除微信绑定与首次登录记录', 'delelte_promoter_wechat'))
    delete_promoter_xshare_fans = ChineseTuple(('删除锁粉信息', 'delete_promoter_xshare_fans'))
    delete_promoter_all_fans = ChineseTuple(('删除推广人下全部粉丝', 'delete_promoter_all_fans'))
    delete_promoter_order = ChineseTuple(('删除推广人下所有分佣记录', 'delete_promoter_order'))
    delete_promoter_openidOrUnionId = ChineseTuple(('推广人账号解绑wechatInfo', 'delete_promoter_openidOrUnionId'))
    reset_promoter_amount_to_0 = ChineseTuple(('重置推广人金额为0', 'reset_promoter_amount_to_0'))
    update_promoter_level_to_partner = ChineseTuple(('推广人修改为合伙人', 'update_promoter_level_to_partner'))
    update_partner_level_to_promoter = ChineseTuple(('合伙人修改为推广人', 'update_partner_level_to_promoter'))
    update_promoter_state_inactive = ChineseTuple(('推广人状态修改为未激活', 'update_promoter_state_inactive'))
    update_promoter_state_active = ChineseTuple(('推广人状态修改为激活', 'update_promoter_state_active'))
    update_promoter_state_frozen = ChineseTuple(('推广人状态修改为已冻结', 'update_promoter_state_frozen'))
    update_promoter_state_forbidden = ChineseTuple(('推广人状态修改为已封号', 'update_promoter_state_forbidden'))
    update_promoter_state_invalid = ChineseTuple(('推广人状态修改为已失效', 'update_promoter_state_invalid'))
    update_promoter = ChineseTuple(('修改推广人信息', 'update_promoter'))


class ReferralOperationEnum(ChineseEnum):
    delete_wc_users = ChineseTuple(('删uid&unionId绑定关系', 'delete_wc_users'))
    delete_xshare_group_purchase = ChineseTuple(('删除团单', 'delete_xshare_group_purchase'))
    reset_xshare_group_purchase = ChineseTuple(('删除参团信息', 'reset_xshare_group_purchase'))
    delete_xshare_screenshot_history_newest = ChineseTuple(('删除截图表中最新一条记录', 'delete_xshare_screenshot_history_newest'))
    update_pingxxorder_cts = ChineseTuple(('修改完课返现时间(默认提前一周)', 'update_pingxxorder_cts'))
    delete_unionId = ChineseTuple(('删除unionId对应绑定关系', 'delete_unionId'))


class InterfaceEnum(ChineseEnum):
    refund = ChineseTuple(('订单退款', 'refund'))
    redeem = ChineseTuple(('生成兑换码', 'redeem'))
    trace_seller_ship = ChineseTuple(('聚水潭发货', 'trace_seller_ship'))


class ESSynchronizeData(ChineseEnum):
    # 班主任
    # ESSync_student = ChineseTuple(('更新学员表ES', 'ESSync_student'))
    ESSync_refund_order = ChineseTuple(('退款订单更新数据', 'ESSync_refund_order'))
    ESSync_student_english = ChineseTuple(('(班主任)更新学员表ES-英语', 'ESSync_student_english'))
    ESSync_student_math = ChineseTuple(('(班主任)更新学员表ES-数学', 'ESSync_student_math'))
    # ESSync_student = ChineseTuple(('更新学员表ES', ['python3 /crm/srv/thrall/app/es/student_db_to_es.py init', 'python3 /crm/srv/thrall/app/es/math_student_db_to_es.py init']))
    ESSync_app_performance = ChineseTuple(('(班主任)更新站内绩效订单ES', 'ESSync_app_performance'))
    ESSync_performance = ChineseTuple(('(班主任)更新认领绩效订单ES', 'ESSync_performance'))
    # 规划师
    ESSync_activity_info = ChineseTuple(('(规划师)活动明细表', 'ESSync_activity_info'))
    ESSync_finish_info = ChineseTuple(('(规划师)完课信息数据', 'ESSync_finish_info'))
    ESSync_no_person = ChineseTuple(('(规划师)待认领订单', 'ESSync_no_person'))
    ESSync_youzan_order = ChineseTuple(('(规划师)有赞订单数据', 'ESSync_youzan_order'))
    ESSync_app_order = ChineseTuple(('(规划师)App订单数据', 'ESSync_app_order'))
    ESSync_student_en_ghs = ChineseTuple(('(规划师)同步英语学员表es', 'ESSync_student_en_ghs'))
    ESSync_math_en_ghs = ChineseTuple(('(规划师)同步思维学员表es', 'ESSync_math_en_ghs'))
    # 推广人
    ESSync_prometer_info = ChineseTuple(('(推广人)推广人信息表es', 'ESSync_prometer_info'))

    # 客服


class LessonCentralEnum(ChineseEnum):
    # 瓜美2。5上线接口
    lesson_get_baby_lesson_info = ChineseTuple(('接口1:getBabyLessonInfo', 'lesson_get_baby_lesson_info'))
    lesson_get_baby_lesson_info_list = ChineseTuple(('接口2:getBabyLessonInfoList', 'lesson_get_baby_lesson_info_list'))
    lesson_get_baby_sublesson_info = ChineseTuple(('接口3:getBabySublessonInfo', 'lesson_get_baby_sublesson_info'))
    lesson_batch_get_sublesson_info = ChineseTuple(('接口4:batchGetSublessonInfo', 'lesson_batch_get_sublesson_info'))
    lesson_section_complete = ChineseTuple(('接口5:sectionComplete', 'lesson_section_complete'))
    lesson_sublesson_complete = ChineseTuple(('接口6:sublessonComplete 完课记录', 'lesson_sublesson_complete'))
    lesson_get_userlesson_buy_info = ChineseTuple(('接口7:getUserLessonBuyInfo', 'lesson_get_userlesson_buy_info'))
    lesson_create = ChineseTuple(('接口8:create 给lessonbuy增加课程', 'lesson_create'))
    lesson_remove = ChineseTuple(('接口9:remove 删除uid对应的购买记录', 'lesson_remove'))
    # 思维新增接口
    lesson_maSectionComplete = ChineseTuple(('思维新增:maSectionComplete 思维section级别完课上报', 'lesson_maSectionComplete'))
    lesson_getMaDaily = ChineseTuple(('思维新增:getMaDaily思维学习报告-获取baby日报互动模块统计信息', 'lesson_getMaDaily'))
    lesson_getMaSwtinyTeacher = ChineseTuple(('思维新增:getMaSwtinyTeacher思维学习报告-获取小小老师音频问答信息', 'lesson_getMaSwtinyTeacher'))
    # 公共新增接口
    lesson_batchGetLevelInfo = ChineseTuple(('公共新增:batchGetLevelInfo根据levelId数组获取level信息', 'lesson_batchGetLevelInfo'))
    lesson_getBabyStudyReportInfo = ChineseTuple(('公共新增:根据babyId和lessonId获取学习报告', 'lesson_getBabyStudyReportInfo'))
    # 游乐场接口
    lesson_getStudyFlowByBidAndKnowledgeId = ChineseTuple(('根据babyId和knowledgeId以及一大坨参数获取学习流水', 'lesson_getStudyFlowByBidAndKnowledgeId'))
    lesson_getStudyFlowByBidAndSublessonId = ChineseTuple(('根据babyId和sublessonId获取学习流水', 'lesson_getStudyFlowByBidAndSublessonId'))
    lesson_getNewerStudyRecordByBid = ChineseTuple(('根据babyId获取最新的学习数据', 'lesson_getNewerStudyRecordByBid'))
    lesson_getNewerStudyRecordByBidAndSkillIds = ChineseTuple(('根据babyId和skillId获取最新的学习数据', 'lesson_getNewerStudyRecordByBidAndSkillIds'))
    lesson_sendMetaKnowledgeAndSkillToMQ = ChineseTuple(('发送全量的知识点/技能点配置信息到MQ', 'lesson_sendMetaKnowledgeAndSkillToMQ'))
    lesson_getTodayStudyFlow = ChineseTuple(('获取学生当天的学习流水', 'lesson_getTodayStudyFlow'))
    # 新版英语section上报接口
    lesson_geSectionComplete = ChineseTuple(('英语新上报接口', 'lesson_geSectionComplete'))
    lesson_getLevelMetaInfo = ChineseTuple(('获取级别基本信息', 'lesson_getLevelMetaInfo'))
    lesson_getWeekMetaInfo = ChineseTuple(('获取周基本信息', 'lesson_getWeekMetaInfo'))
    lesson_getLessonMetaInfo = ChineseTuple(('获取课程基本信息', 'lesson_getLessonMetaInfo'))
    lesson_getSublessonMetaInfo = ChineseTuple(('获取子课程基本信息', 'lesson_getSublessonMetaInfo'))
    lesson_getSublessonTypeInfo = ChineseTuple(('获取子课程类型基本信息', 'lesson_getSublessonTypeInfo'))
    lesson_getSublessonTypeMetaInfoList = ChineseTuple(('获取子课程类型集合的基本信息', 'lesson_getSublessonTypeMetaInfoList'))
    # 9.9和abTest获取用户数据
    lesson_getBabyLessonInfoListV2 = ChineseTuple(('根据levelId返回level下lesson的信息(完课+没完课)', 'lesson_getBabyLessonInfoListV2'))
    lesson_batchGetSublessonInfoV2 = ChineseTuple(('需要获取学习数据，按照子课程顺序排序，并判断解锁状态', 'lesson_batchGetSublessonInfoV2'))
    # 竖版路线图
    lesson_getLevelListInfoBySubject = ChineseTuple(('根据subject获取level数组', 'lesson_getLevelListInfoBySubject'))
    lesson_getWeekAndLevelInfoByNum = ChineseTuple(('根据weekNum获取当前level信息以及当前周基本信息', 'lesson_getWeekAndLevelInfoByNum'))
    # 9.9和abTest的影响接口
    lesson_sublessonCompleteV2 = ChineseTuple(('sublesson的上报', 'lesson_sublessonCompleteV2'))
    lesson_getBabyStudyReportInfoV2 = ChineseTuple(('根据babyId和lessonId获取学习报告', 'lesson_getBabyStudyReportInfoV2'))
    # 拓展tab相关接口
    lesson_getChildrenSongInfoList = ChineseTuple(('根据level_id, 获取所有的儿歌数据', 'lesson_getChildrenSongInfoList'))
    # 内部rest接口
    lesson_knowledgeGeMessageForward = ChineseTuple(('知识点数据修改转发', 'lesson_knowledgeGeMessageForward'))
    lesson_skillGeMessageForward = ChineseTuple(('技能点数据修改转发', 'lesson_skillGeMessageForward'))
    # 游乐场上报（支持预测分和资源id）
    lesson_playGroundSectionComplete = ChineseTuple(('专属游乐场的上报接口', 'lesson_playGroundSectionComplete'))
    # Server技改需求
    lesson_getWeekNumByType = ChineseTuple(('根据level和weekType获取周数', 'lesson_getWeekNumByType'))
    lesson_getBabyLessonInfoListV3 = ChineseTuple(('根据levelId和lesson数组返回level下lesson的信息', 'lesson_getBabyLessonInfoListV3'))
    lesson_getMetaLevelWeekInfo = ChineseTuple(('获取课程大纲内容和周主题等', 'lesson_getMetaLevelWeekInfo'))
    # Cocos资源包
    lesson_getPackagesByGameId = ChineseTuple(('根据gameId获取资源包信息', 'lesson_getPackagesByGameId'))
    # 11.5上线接口
    lesson_geBabyStudyReport = ChineseTuple(('获取英语课后报告（包括）', 'lesson_geBabyStudyReport'))
    lesson_ywSectionComplete = ChineseTuple(('语文上报', 'lesson_ywSectionComplete'))
    lesson_bacthSubLessonComplete = ChineseTuple(('sublesson和lesson级别完课', 'lesson_bacthSubLessonComplete'))


class eshopEnum(ChineseEnum):
    create_SGU = ChineseTuple(('创建SGU', 'create_SGU'))
    create_SPU = ChineseTuple(('创建SPU', 'create_SPU'))


class saturnEnum(ChineseEnum):
    saturn_bind = ChineseTuple(('下沉锁粉', 'saturn_bind'))

class BusinessEnum(ChineseEnum):
    general = ChineseTuple(('通用', GeneralOperationEnum))
    promoter = ChineseTuple(('推广人', PromoterOperationEnum))
    referral = ChineseTuple(('转介绍', ReferralOperationEnum))
    interface = ChineseTuple(('接口操作', InterfaceEnum))
    eshop = ChineseTuple(('交易中台', eshopEnum))
    saturn = ChineseTuple(('下沉', saturnEnum))
    lesson_central = ChineseTuple(('课程中台操作', LessonCentralEnum))
    es_sync_data = ChineseTuple(('ES同步数据', ESSynchronizeData))


class CategoryEnum(ChineseEnum):
    """科目属性"""
    english = ChineseTuple(('英语', 1))
    reading = ChineseTuple(('阅读', 2))
    thinking = ChineseTuple(('思维', 3))
    yuwen = ChineseTuple(('语文', 4))
    virtual_card = ChineseTuple(('虚拟卡', 5))
    other = ChineseTuple(('其他', 6))
    thinking_english = ChineseTuple(('思维+英语', 7))


class SubjectSp2xuidsEnum(ChineseEnum):
    """科目对应Sp2xuids枚举"""
    english = ChineseTuple(('英语', [2819]))
    thinking = ChineseTuple(('思维', [2821]))
    thinking_english = ChineseTuple(('英语+思维', [3388]))
