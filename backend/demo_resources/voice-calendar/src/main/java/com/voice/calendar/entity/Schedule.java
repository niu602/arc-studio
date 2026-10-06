package com.voice.calendar.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableLogic;
import java.io.Serializable;
import java.time.LocalDateTime;
import lombok.Data;
import org.apache.ibatis.type.JdbcType;

/**
 * <p>
 * 日程表
 * </p>
 *
 * @author yourname
 * @since 2026-05-29
 */
@Data
@TableName("schedule") // 关键：指定表名
public class Schedule implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 日程ID
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 日程标题
     */
    private String title;

    /**
     * 日程内容
     */
    @TableField(jdbcType = JdbcType.LONGVARCHAR)
    private String content;

    /**
     * 地点
     */
    private String location;

    /**
     * 开始时间
     */
    private LocalDateTime startTime;

    /**
     * 结束时间
     */
    private LocalDateTime endTime;

    /**
     * 是否重复(0-否 1-是)
     */
    private Byte isRepeat;

    /**
     * 重复类型(DAILY/WEEKLY/MONTHLY/YEARLY)
     */
    private String repeatType;

    /**
     * 提前提醒分钟数(0-不提醒)
     */
    private Integer remindMinutes;

    /**
     * 状态(0-已取消 1-待进行 2-已完成)
     */
    private Byte status;

    /**
     * 创建时间
     */
    @TableField("created_at") // 显式映射字段
    private LocalDateTime createdAt;

    /**
     * 更新时间
     */
    @TableField("updated_at") // 显式映射字段
    private LocalDateTime updatedAt;

    /**
     * 逻辑删除(0-未删除 1-已删除)
     */
    @TableLogic // 标记逻辑删除字段
    private Byte isDeleted;

    /**
     * 日程类型：alarm/work/birthday/todo，默认todo
     */
    private String type;

    /**
     * 是否已完成
     */
    @TableField("is_done")
    private Boolean isDone;


}