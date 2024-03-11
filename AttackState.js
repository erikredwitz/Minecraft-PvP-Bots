// Build the state
const attackState = (function(){
    function AttackState(bot)
    {
        this.bot = bot;
        this.active = false;
        this.stateName = 'AttackState';
    }

    AttackState.prototype.onStateEntered = function () {
        console.log(`${bot.username} has entered the ${this.stateName} state.`);
    };
    AttackState.prototype.onStateExited = function () {
        console.log(`${bot.username} has left the ${this.stateName} state.`);
    };

    return AttackState;
}());

// Creating a new instance
const attackStateIndex = new attackState(bot /* your bot */);