package com.voice.calendar;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.voice.calendar.mapper")
public class VoiceCalendarApplication {
    public static void main(String[] args) {
        SpringApplication.run(VoiceCalendarApplication.class, args);
    }
}