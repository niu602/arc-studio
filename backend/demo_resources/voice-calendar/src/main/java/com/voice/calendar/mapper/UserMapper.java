package com.voice.calendar.mapper;

import com.voice.calendar.entity.User;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

/**
 * <p>
 * 用户表 Mapper 接口
 * </p>
 *
 * @author yourname
 * @since 2026-05-29
 */
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserMapper extends BaseMapper<User> {
    //查询用户
    @Select("SELECT * FROM user WHERE phone = #{phone}")
    User selectByPhone(String phone);
}