const { main } = require('../src/index.js');

describe('main', () => {
    test('main function exists', () => {
        expect(typeof main).toBe('function');
    });

    test('main runs without error', () => {
        expect(() => main()).not.toThrow();
    });

    test('basic math', () => {
        expect(1 + 1).toBe(2);
    });
});