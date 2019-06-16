
perm: int128

#@ invariant: forall({axiom: int128, mp: map(int128, uint256)}, {mp[axiom]}, mp[axiom] == mp[axiom])

@public
def assume():
    pass

@public
def acc():
    domain: int128