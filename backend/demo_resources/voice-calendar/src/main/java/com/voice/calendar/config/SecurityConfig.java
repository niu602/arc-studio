package com.voice.calendar.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Collections;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                // Spring Security 6.x 新写法：启用CORS并使用我们的配置
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                // 关闭CSRF（前后端分离项目不需要）
                .csrf(csrf -> csrf.disable())
                // 允许所有请求
                .authorizeHttpRequests(auth -> auth
                        .anyRequest().permitAll()
                );

        return http.build();
    }

    // 正确的CORS配置（Spring Boot 3.x 专用）
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();

        // ✅ 唯一正确的写法：用 setAllowedOriginPatterns，绝对不能用 addAllowedOrigin("*")
        config.setAllowedOriginPatterns(Collections.singletonList("*"));
        // 允许所有HTTP方法
        config.setAllowedMethods(Collections.singletonList("*"));
        // 允许所有请求头
        config.setAllowedHeaders(Collections.singletonList("*"));
        // 允许前端携带Token/Cookie
        config.setAllowCredentials(true);
        // 预检请求缓存1小时
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}