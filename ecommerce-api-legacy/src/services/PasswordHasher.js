'use strict';

const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);

/**
 * Password hashing with scrypt (playbook RP-12).
 *
 * Replaces `badCrypto`, which concatenated the first two characters of the
 * password's Base64 encoding 10,000 times — always the same pair, no salt,
 * and deterministic enough to be inverted by table lookup.
 *
 * scrypt ships with Node's standard library, so there is no new native
 * dependency to compile. It is a memory-hard KDF, designed to be slow.
 */

const KEY_LENGTH = 64;
const SALT_LENGTH = 16;
const PREFIX = 'scrypt';

async function hashPassword(senha, custo = 12) {
    const salt = crypto.randomBytes(SALT_LENGTH).toString('hex');
    // scrypt's cost is a power of two; the bcrypt-style "rounds" parameter
    // is converted to the equivalent scale.
    const N = 2 ** Math.min(Math.max(custo, 10), 16);
    const derivada = await scrypt(senha, salt, KEY_LENGTH, { N, r: 8, p: 1, maxmem: 256 * 1024 * 1024 });
    return `${PREFIX}$${N}$${salt}$${derivada.toString('hex')}`;
}

async function verifyPassword(senha, armazenada) {
    if (typeof armazenada !== 'string' || !armazenada.startsWith(`${PREFIX}$`)) {
        return false;
    }

    const [, custo, salt, esperada] = armazenada.split('$');
    const derivada = await scrypt(senha, salt, KEY_LENGTH, {
        N: Number(custo),
        r: 8,
        p: 1,
        maxmem: 256 * 1024 * 1024,
    });

    // Constant-time comparison: === short-circuits at the first differing
    // byte and leaks information through timing.
    const esperadaBuffer = Buffer.from(esperada, 'hex');
    return esperadaBuffer.length === derivada.length
        && crypto.timingSafeEqual(esperadaBuffer, derivada);
}

module.exports = { hashPassword, verifyPassword };
