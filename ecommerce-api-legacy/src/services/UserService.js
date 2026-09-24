'use strict';

const { NotFoundError } = require('../middlewares/errors');
const { logger } = require('../infra/logger');

class UserService {
    constructor({ userRepository }) {
        this.userRepository = userRepository;
    }

    /**
     * Removes the user logically.
     *
     * Physical deletion corrupted the financial report: enrollments and
     * payments kept pointing at a nonexistent id.
     */
    async remove(id) {
        const usuario = await this.userRepository.findById(id);
        if (!usuario) {
            throw new NotFoundError('Usuário não encontrado');
        }

        await this.userRepository.deactivate(id);
        logger.info('user.desativado', { userId: Number(id) });

        return { msg: 'Usuário desativado. Matrículas e pagamentos preservados.' };
    }
}

module.exports = { UserService };
