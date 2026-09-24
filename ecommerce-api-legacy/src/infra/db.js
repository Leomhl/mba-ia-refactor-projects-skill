'use strict';

const sqlite3 = require('sqlite3');

/**
 * Promisified SQLite connection (playbook RP-10).
 *
 * The driver only enters verbose mode when configuration asks for it: that
 * mode attaches a JavaScript stack trace to errors, which used to reach the
 * client.
 */
function createDatabase(config) {
    const driver = config.db.verbose ? sqlite3.verbose() : sqlite3;
    const db = new driver.Database(config.db.path);

    const all = (sql, params = []) =>
        new Promise((resolve, reject) => {
            db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        });

    const get = (sql, params = []) =>
        new Promise((resolve, reject) => {
            db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });

    // `promisify` over db.run would discard the `this` carrying lastID and
    // changes, so the wrapper is manual.
    const run = (sql, params = []) =>
        new Promise((resolve, reject) => {
            db.run(sql, params, function (err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });

    const exec = (sql) =>
        new Promise((resolve, reject) => {
            db.exec(sql, (err) => (err ? reject(err) : resolve()));
        });

    /**
     * Runs the callback inside a transaction, rolling back on error.
     * Replaces the non-atomic INSERT chains (playbook RP-08).
     */
    const transaction = async (callback) => {
        await run('BEGIN');
        try {
            const resultado = await callback();
            await run('COMMIT');
            return resultado;
        } catch (erro) {
            await run('ROLLBACK');
            throw erro;
        }
    };

    const close = () =>
        new Promise((resolve, reject) => {
            db.close((err) => (err ? reject(err) : resolve()));
        });

    return { all, get, run, exec, transaction, close, raw: db };
}

module.exports = { createDatabase };
