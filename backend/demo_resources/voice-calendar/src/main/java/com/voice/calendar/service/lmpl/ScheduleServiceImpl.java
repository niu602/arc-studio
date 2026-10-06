package com.voice.calendar.service.lmpl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.voice.calendar.entity.Schedule;
import com.voice.calendar.mapper.ScheduleMapper;
import com.voice.calendar.service.ScheduleService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class ScheduleServiceImpl extends ServiceImpl<ScheduleMapper, Schedule> implements ScheduleService {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    // ======================= 查询日程（带 userId） =======================
    public List<Schedule> findByTimeRangeAndContent(
            String startTimeStr,
            String endTimeStr,
            String content,
            Long userId
    ) {
        LocalDateTime startTime = null;
        LocalDateTime endTime = null;

        if (startTimeStr != null) {
            startTime = LocalDateTime.parse(startTimeStr, FORMATTER);
        }
        if (endTimeStr != null) {
            endTime = LocalDateTime.parse(endTimeStr, FORMATTER);
        }
        //调用baseMapper查询数据库
        return baseMapper.selectByTimeRangeAndContent(userId, startTime, endTime, content);
    }

    // ======================= 删除日程（带 userId） =======================
    public boolean deleteById(Long id, Long userId) {
        return baseMapper.deleteById(id, userId) > 0;
    }
}