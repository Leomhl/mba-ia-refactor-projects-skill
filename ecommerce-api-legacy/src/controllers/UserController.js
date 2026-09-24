'use strict';

const { ValidationError } = require('../middlewares/errors');

class UserController {
    constructor({ userService }) {
        this.userService = userService;
        this.remove = this.remove.bind(this);
    }

    async remove(req, res, next) {
        try {
            const id = Number(req.params.id);
            if (!Number.isInteger(id) || id < 1) {
                throw new ValidationError('Id inválido');
            }

            res.status(200).json(await this.userService.remove(id));
        } catch (erro) {
            next(erro);
        }
    }
}

module.exports = { UserController };
