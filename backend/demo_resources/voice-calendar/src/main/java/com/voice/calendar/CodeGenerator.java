package com.voice.calendar;

import com.baomidou.mybatisplus.generator.FastAutoGenerator;
import com.baomidou.mybatisplus.generator.config.OutputFile;
import com.baomidou.mybatisplus.generator.engine.VelocityTemplateEngine;

import java.util.Collections;

public class CodeGenerator {
    public static void main(String[] args) {
        // 数据库连接配置（和application.yml里的一致）
        String url = "jdbc:mysql://localhost:3306/voice_calendar?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true";
        String username = "root";
        String password = "Niuzisen123";
        String parentPackage = "com.voice.calendar"; // 父包名

        FastAutoGenerator.create(url, username, password)
                // 全局配置
                .globalConfig(builder -> {
                    builder.author("yourname")
                            .outputDir(System.getProperty("user.dir") + "/src/main/java") // 输出目录
                            .disableOpenDir(); // 生成后不打开目录
                })
                // 包配置
                .packageConfig(builder -> {
                    builder.parent(parentPackage)
                            .controller("controller")
                            .service("service")
                            .serviceImpl("service.impl")
                            .mapper("mapper")
                            .entity("entity")
                            .xml("mapper");
                })
                // 策略配置（适配3.5.5版本）
                .strategyConfig(builder -> {
                    builder.addInclude("user","schedule")
                            // 实体类配置
                            .entityBuilder()
                            .enableLombok() // 启用Lombok
                            .controllerBuilder()
                            .enableRestStyle() // Rest风格
                            .serviceBuilder()
                            .formatServiceFileName("%sService")
                            .mapperBuilder();
                })
                // 模板引擎
                .templateEngine(new VelocityTemplateEngine())
                .execute();
    }
}