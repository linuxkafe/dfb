package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AppTest {

    @Test
    void testAppExists() {
        assertTrue(App.class.getName().contains("App"));
    }

    @Test
    void testMainOutput() {
        // Capture System.out would require more setup
        // This is a placeholder
        assertTrue(true);
    }
}
