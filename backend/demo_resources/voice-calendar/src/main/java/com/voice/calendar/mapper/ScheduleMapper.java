package com.voice.calendar.mapper;

import com.voice.calendar.entity.Schedule;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface ScheduleMapper extends BaseMapper<Schedule> {

    // 根据用户id查询日程
    @Select("SELECT * FROM schedule WHERE user_id = #{userId}")
    Schedule selectByUserId(Long userId);

    // 根据开始时间、结束时间、内容、用户ID动态查询日程
    @Select({
            "<script>",
            "SELECT * FROM schedule ",
            "WHERE user_id = #{userId} ",//只查当前用户数据
            "<if test=\"startTime != null\">AND start_time &gt;= #{startTime}</if> ",
            "<if test=\"endTime != null\">AND end_time &lt;= #{endTime}</if> ",
            "<if test=\"content != null\">AND content LIKE CONCAT('%', #{content}, '%')</if> ",
            "ORDER BY start_time ASC",
            "</script>"
    })
    List<Schedule> selectByTimeRangeAndContent(
            @Param("userId") Long userId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            @Param("content") String content
    );

    /**
     * 根据 ID + userId 删除日程
     */
    @Delete("DELETE FROM schedule WHERE id = #{id} AND user_id = #{userId}")
    int deleteById(@Param("id") Long id, @Param("userId") Long userId);
}