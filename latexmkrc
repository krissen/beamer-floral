# The engine is the fork at krissen/tikz-flora, branch beamer-floral,
# commit 136291b or later. Override TIKZFLORA to use another checkout.
my $flora = $ENV{'TIKZFLORA'} || "$ENV{HOME}/dev/tikz-flora";
$ENV{'TEXINPUTS'} = "$flora/tex//:" . (defined $ENV{'TEXINPUTS'} ? $ENV{'TEXINPUTS'} : '');
$ENV{'FLORA_LUA'} = "$flora/lua";
