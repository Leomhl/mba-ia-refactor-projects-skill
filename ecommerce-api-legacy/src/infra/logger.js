'use strict';

const { config } = require('../config');

/**
 * Minimal structured logging (playbook RP-16), with no external dependency.
 *
 * Replaces the template-string `console.log` calls — one of which printed the
 * card number and gateway key in plaintext.
 */
const NIVEIS = { error: 0, warn: 1, info: 2, debug: 3 };

function emitir(nivel, evento, campos = {}) {
    if (NIVEIS[nivel] > (NIVEIS[config.logLevel] ?? NIVEIS.info)) return;

    const linha = JSON.stringify({
        level: nivel,
        event: evento,
        ...campos,
    });

    if (nivel === 'error') process.stderr.write(`${linha}\n`);
    else process.stdout.write(`${linha}\n`);
}

const logger = {
    error: (evento, campos) => emitir('error', evento, campos),
    warn: (evento, campos) => emitir('warn', evento, campos),
    info: (evento, campos) => emitir('info', evento, campos),
    debug: (evento, campos) => emitir('debug', evento, campos),
};

module.exports = { logger };
