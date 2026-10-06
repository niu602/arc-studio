package com.voice.calendar.entity;

import lombok.Data;

/**
 * AI 解析后的日程指令
 * 专门用来接收豆包AI返回的结构化指令
 * 绝对不能删除！核心类！
 */
@Data
public class ScheduleCommand {

    /**
     * 操作类型：add、delete、query、unknown
     */
    private String action;

    /**
     * 开始时间 yyyy-MM-dd HH:mm
     */
    private String startTime;

    /**
     * 结束时间 yyyy-MM-dd HH:mm
     */
    private String endTime;

    /**
     * 日程内容/关键词
     */
    private String content;

    /**
     * 地点
     */
    private String location;
}