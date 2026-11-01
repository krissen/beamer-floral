my $flora = $ENV{'TIKZFLORA'} || "$ENV{HOME}/dev/tikz-flora";
$ENV{'TEXINPUTS'} = "$flora/tex//:" . (defined $ENV{'TEXINPUTS'} ? $ENV{'TEXINPUTS'} : '');
$ENV{'FLORA_LUA'} = "$flora/lua";
