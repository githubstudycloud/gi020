package com.example.config;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.config.server.EnableConfigServer;
import org.springframework.context.annotation.Bean;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Spring Boot 3.x Config Server
 *
 * 3.x 主要变化（相比 2.x）：
 * 1. 需要 Java 17+
 * 2. javax.* 包迁移到 jakarta.* 包
 * 3. Security 配置中废弃了 antMatchers，改用 requestMatchers
 * 4. 支持 GraalVM 原生镜像编译
 * 5. 废弃了部分旧 API（如 WebSecurityConfigurerAdapter 已在 2.7 中废弃，3.x 彻底移除）
 */
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}

/**
 * Spring Security 配置（Spring Boot 3.x / Spring Security 6.x）
 *
 * 3.x 关键变化：
 * - antMatchers → requestMatchers
 * - authorizeRequests → authorizeHttpRequests
 * - WebSecurityConfigurerAdapter 已完全移除
 */
@EnableWebSecurity
class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())  // 3.x lambda DSL
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health", "/actuator/info").permitAll()
                .requestMatchers("/encrypt/**", "/decrypt/**").authenticated()
                .anyRequest().authenticated()
            )
            .httpBasic(basic -> {});  // 3.x lambda DSL
        return http.build();
    }
}
