package com.voice.calendar.service;

import com.voice.calendar.entity.User;
import com.baomidou.mybatisplus.extension.service.IService;
import com.voice.calendar.dto.LoginRequest;
import com.voice.calendar.dto.RegisterRequest;
/**
 * <p>
 * 用户表 服务类
 * </p>
 *
 * @author yourname
 * @since 2026-05-29
 */
public interface UserService extends IService<User> {
    // 发送验证码
    void sendCode(String phone);

    // 注册
    void register(RegisterRequest request);

    // 登录
    String login(LoginRequest request);

    // 检查手机号是否存在
    boolean checkPhoneExists(String phone);
    //根据手机号查用户
    User getUserByPhone(String phone);
}
