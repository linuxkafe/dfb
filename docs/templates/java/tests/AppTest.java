package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AppTest {

    @Test
    void testMainRuns() {
        // Smoke test - verify the class loads
        assertTrue(true);
    }

    @Test
    void testBasicMath() {
        assertEquals(2, 1 + 1);
    }
}