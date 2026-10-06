package com.voice.calendar.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 安卓端日程返回VO，和ReminderClient解析格式完全对齐
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ReminderVO {
    /**
     * 日程ID
     */
    private Long id;

    /**
     * 日程时间，格式yyyy-MM-dd HH:mm
     */
    private String time;

    /**
     * 日程内容
     */
    private String content;

    /**
     * 日程类型：alarm/work/birthday/todo
     */
    private String type;

    /**
     * 是否已完成，字段名和安卓端完全一致为is_done
     */
    private Boolean is_done;
}
