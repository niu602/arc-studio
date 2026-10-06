package com.voice.calendar.service.lmpl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.voice.calendar.dto.LoginRequest;
import com.voice.calendar.dto.RegisterRequest;
import com.voice.calendar.entity.User;
import com.voice.calendar.mapper.UserMapper;
import com.voice.calendar.service.UserService;
import com.voice.calendar.utils.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.Random;
import java.util.concurrent.TimeUnit;

// 关键：继承 ServiceImpl<UserMapper, User> 并实现 UserService
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    @Autowired
    private UserMapper userMapper;
    @Autowired
    private StringRedisTemplate redisTemplate;
    @Autowired
    private JwtUtil jwtUtil;

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    private static final String CODE_PREFIX = "code:";
    private static final long CODE_EXPIRE = 300;
    //发送验证码，5分钟过期
    @Override
    public void sendCode(String phone) {
        String code = String.format("%06d", new Random().nextInt(1000000));
        String key = CODE_PREFIX + phone;
        redisTemplate.opsForValue().set(key, code, CODE_EXPIRE, TimeUnit.SECONDS);
        System.out.println("手机号：" + phone + " 验证码：" + code);
        String checkCode = redisTemplate.opsForValue().get(key);
        System.out.println("存入后Redis中读取到的验证码：" + checkCode);
    }
    //注册服务
    @Override
    public void register(RegisterRequest request) {
        String phone = request.getPhone();
        String pwd = request.getPassword();
        String inputcode = request.getCode();
        String key = CODE_PREFIX + phone;
        // 1. 校验手机号是否已存在
        if (checkPhoneExists(phone)) {
            throw new RuntimeException("手机号已注册");
        }
        String realCode = redisTemplate.opsForValue().get(key);
        System.out.println("Redis中的验证码：" + realCode + "，前端传的：" + inputcode);
        if (realCode == null || !realCode.equals(inputcode)) {
            System.out.println("验证码校验失败，抛出异常");
            throw new RuntimeException("验证码错误或已过期");
        }
        //密码加密（BCrypt）
        User user = new User();
        user.setPhone(phone);
        user.setPassword(encoder.encode(pwd));
        // 保存用户到数据库
        System.out.println("所有校验通过，准备插入用户");
        save(user);
        //删除用过的验证码
        redisTemplate.delete(key);
    }
    //登录服务
    @Override
    public String login(LoginRequest request) {
        //根据手机号查用户
        User user = lambdaQuery().eq(User::getPhone, request.getPhone()).one();
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        //密码比对
        if (!encoder.matches(request.getPassword(), user.getPassword())) {
            throw new RuntimeException("密码错误");
        }
        //生成JWT Token并返回
        return jwtUtil.generateToken(user.getId(), user.getPhone());
    }
    //判断手机号是否已被占用
    @Override
    public boolean checkPhoneExists(String phone) {
        return lambdaQuery().eq(User::getPhone, phone).count() > 0;
    }

    @Override
    public User getUserByPhone(String phone) {
        // 在这里调用Mapper的selectByPhone方法
        return userMapper.selectByPhone(phone);
    }
}