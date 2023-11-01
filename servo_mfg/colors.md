# Guidelines on how to use colors in manufacturing scripts

These guidelines are to make sure that all scripts run similarly and a color
usually has similar meaning. If that's not possible, try to amend the
guidelines, amend the script, or expand the number of colors used. Not
everything is applicable to all servo devices (e.g. servo micro has no DUT
power connection)

1.  blue\
    blue should be used for the DFU mode connection (switch, or cable)
2.  red\
    red should be used for the host normal mode connection
3.  green\
    green should be used for the DUT power (hub servos: v4, v4p1) connection
4.  magenta\
    magenta should be used to mark the DUT connection (pigtail on hub servos)
5.  yellow\
    yellow should be used to mark the peripherals that need to be attached for
    testing e.g. usb-sticks, dongles, etc.


## prompts and results

In colormode the result is printed on a red/green background (depending on
success or failure). Additionally, user prompts (which are always prefaced with
`>>>` have that sequence now on a red background as well to inform the user they
need to take action
