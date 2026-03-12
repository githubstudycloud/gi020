package com.example.config;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.config.server.EnableConfigServer;
import org.springframework.context.annotation.Bean;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Spring Boot 2.x Config Server
 *
 * 2.x 变化：
 * 1. Security 配置使用 SecurityFilterChain（Spring Security 5.7+）
 * 2. Actuator 端点路径统一为 /actuator/*
 * 3. 新增 /actuator/bus-refresh 支持（配合 Spring Cloud Bus）
 */
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}

/**
 * Spring Security 配置（Spring Boot 2.7.x 推荐方式）
 * 保护 /encrypt /decrypt 端点，开放健康检查
 */
@EnableWebSecurity
class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf().disable()
            .authorizeRequests()
                // 开放健康检查
                .antMatchers("/actuator/health").permitAll()
                // 加密端点需要认证
                .antMatchers("/encrypt/**", "/decrypt/**").authenticated()
                // Config 数据端点也需要认证
                .anyRequest().authenticated()
            .and()
            .httpBasic();  // 使用 HTTP Basic 认证
        return http.build();
    }
}
